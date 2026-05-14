"""
import_wizard.py — معالج الاستيراد الجماعي للطلاب من Excel/CSV

الخطوات:
  1. اختيار الملف (Excel .xlsx أو CSV)
  2. معاينة البيانات + تعيين الأعمدة (column mapping)
  3. التحقق (validators.py) وعرض الأخطاء صف بصف
  4. الاستيراد الفعلي مع تقرير النتائج

التوافق مع المخطط:
  - Students: first_name_fr, last_name_fr, first_name_ar, last_name_ar,
              birth_date (DATE), birth_place, gender, address,
              parent_name, parent_phone, parent_email, parent_address,
              status='Active'
  - StudentClassNumbers: student_id, class_id, year_id, class_number
  - is_active في AcademicYears هو INTEGER (0/1)
  - Staff.status = 'Actif' — غير مستخدم هنا
"""

import os
import csv
from datetime import datetime, date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QComboBox,
    QProgressBar, QTextEdit, QMessageBox, QFrame, QScrollArea,
    QWidget, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from database_setup import DatabaseManager, log_audit
from app_logger import AppLogger
from validators import validate_student, format_errors
from ui_styles import ThemeManager
from repositories.import_wizard_repo import ImportWizardRepository

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# --- أعمدة الطالب المتاحة للتعيين ---
STUDENT_FIELDS = [
    ("",                 "— Ignorer cette colonne —"),
    ("first_name_fr",    "Prénom (FR) *"),
    ("last_name_fr",     "Nom de famille (FR) *"),
    ("first_name_ar",    "الاسم الأول (AR) *"),
    ("last_name_ar",     "اسم العائلة (AR) *"),
    ("birth_date",       "Date de naissance (AAAA-MM-JJ)"),
    ("birth_place",      "Lieu de naissance"),
    ("gender",           "Sexe (M / F)"),
    ("address",          "Adresse"),
    ("parent_name",      "Nom du parent / tuteur"),
    ("parent_phone",     "Téléphone parent"),
    ("parent_email",     "Email parent"),
    ("parent_address",   "Adresse parent"),
]
FIELD_KEYS   = [f[0] for f in STUDENT_FIELDS]
FIELD_LABELS = [f[1] for f in STUDENT_FIELDS]


def _parse_date(raw) -> str | None:
    """تحويل قيمة خلية إلى سلسلة YYYY-MM-DD أو None"""
    if raw is None:
        return None
    if isinstance(raw, (datetime, date)):
        return raw.strftime("%Y-%m-%d")
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s or None


def _normalize_gender(raw) -> str:
    """تطبيع قيمة الجنس إلى M أو F"""
    if raw is None:
        return ""
    s = str(raw).strip().upper()
    if s in ("M", "MASCULIN", "MALE", "ذكر"):
        return "M"
    if s in ("F", "FEMININ", "FÉMININ", "FEMALE", "أنثى", "FILLE"):
        return "F"
    return s


class ImportWorker(QThread):
    """خيط الخلفية لتنفيذ الاستيراد الفعلي"""
    progress    = pyqtSignal(int)          # 0-100
    row_result  = pyqtSignal(int, bool, str)   # row_index, success, message
    finished_sig = pyqtSignal(int, int)    # imported, failed

    def __init__(self, rows: list[dict], class_id: int, year_id: int, actor: str):
        super().__init__()
        self.rows     = rows
        self.class_id = class_id
        self.year_id  = year_id
        self.actor    = actor

    def run(self):
        imported = 0
        failed   = 0
        total    = len(self.rows)

        db = DatabaseManager()
        for idx, data in enumerate(self.rows):
            try:
                with db.get_connection() as conn:
                    repo = ImportWizardRepository(conn)

                    # احتساب رقم الطالب التالي في الفصل
                    next_num = repo.get_next_class_number(self.class_id, self.year_id)

                    # إدراج الطالب
                    student_id = repo.insert_student(data)

                    # ربط الطالب بالفصل والسنة
                    repo.insert_student_class_number(student_id, self.class_id, self.year_id, next_num)

                    log_audit(conn, self.actor, "IMPORT_STUDENT",
                              f"{data.get('first_name_fr','')} {data.get('last_name_fr','')} (id={student_id})")
                    conn.commit()

                imported += 1
                self.row_result.emit(idx, True, f"id={student_id}")
            except Exception as e:
                failed += 1
                self.row_result.emit(idx, False, str(e))
                AppLogger.error("ImportWizard", f"Row {idx}: {e}")

            self.progress.emit(int((idx + 1) * 100 / total))

        self.finished_sig.emit(imported, failed)


class ImportWizard(QDialog):
    """
    معالج الاستيراد الجماعي للطلاب.
    الاستخدام:
        wiz = ImportWizard(parent=self, actor="admin")
        wiz.exec()
    """

    def __init__(self, parent=None, actor: str = "system"):
        super().__init__(parent)
        self.actor    = actor
        self.setWindowTitle("📥  Importation en masse / استيراد جماعي")
        self.setMinimumSize(950, 680)
        self.setModal(True)
        ThemeManager.apply_theme(self)

        self._raw_headers: list[str] = []
        self._raw_rows:    list[list] = []
        self._mapping_combos: list[QComboBox] = []
        self._validated_rows: list[dict] = []  # صفوف صالحة بعد التحقق
        self._worker: ImportWorker | None = None

        self._build_ui()
        self._load_classes_and_years()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        colors = ThemeManager.get_colors()
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # — عنوان —
        lbl = QLabel("📥  Importation en masse des élèves / استيراد جماعي للطلاب")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {colors.TEXT_PRIMARY};")
        root.addWidget(lbl)

        # — الخط الفاصل —
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {colors.BORDER}; max-height: 1px;")
        root.addWidget(sep)

        # — صف: اختيار الملف —
        file_row = QHBoxLayout()
        self.lbl_file = QLabel("Aucun fichier sélectionné")
        self.lbl_file.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-style: italic;")
        btn_browse = QPushButton("📂  Choisir fichier (.xlsx / .csv)")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet(self._btn_style(colors.PRIMARY))
        btn_browse.clicked.connect(self._browse_file)
        file_row.addWidget(self.lbl_file, 1)
        file_row.addWidget(btn_browse)
        root.addLayout(file_row)

        # — سطر: الفصل والسنة الدراسية —
        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel("Classe:"))
        self.combo_class = QComboBox()
        self.combo_class.setMinimumWidth(180)
        self.combo_class.setStyleSheet(self._combo_style(colors))
        dest_row.addWidget(self.combo_class)
        dest_row.addSpacing(20)
        dest_row.addWidget(QLabel("Année:"))
        self.combo_year = QComboBox()
        self.combo_year.setMinimumWidth(130)
        self.combo_year.setStyleSheet(self._combo_style(colors))
        dest_row.addWidget(self.combo_year)
        dest_row.addStretch()
        root.addLayout(dest_row)

        # — منطقة تعيين الأعمدة —
        lbl_map = QLabel("Correspondance des colonnes / تعيين الأعمدة:")
        lbl_map.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY};")
        root.addWidget(lbl_map)

        self.mapping_scroll = QScrollArea()
        self.mapping_scroll.setWidgetResizable(True)
        self.mapping_scroll.setMaximumHeight(160)
        self.mapping_scroll.setStyleSheet("border: none; background: transparent;")
        self.mapping_container = QWidget()
        self.mapping_layout = QHBoxLayout(self.mapping_container)
        self.mapping_layout.setContentsMargins(0, 0, 0, 0)
        self.mapping_layout.setSpacing(10)
        self.mapping_scroll.setWidget(self.mapping_container)
        root.addWidget(self.mapping_scroll)

        # — معاينة (أول 10 صفوف) —
        lbl_prev = QLabel("Aperçu (10 premières lignes) / معاينة:")
        lbl_prev.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY};")
        root.addWidget(lbl_prev)

        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(200)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.preview_table)

        # — شريط التقدم —
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ border-radius: 5px; background: {colors.INPUT_BG}; height: 18px; text-align: center; }}
            QProgressBar::chunk {{ background: {colors.SUCCESS}; border-radius: 5px; }}
        """)
        root.addWidget(self.progress_bar)

        # — سجل النتائج —
        lbl_log = QLabel("Résultats / النتائج:")
        lbl_log.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY};")
        root.addWidget(lbl_log)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet(f"background: {colors.INPUT_BG}; color: {colors.TEXT_SECONDARY}; border-radius: 6px; padding: 5px;")
        root.addWidget(self.log_text)

        # — أزرار الأسفل —
        btn_row = QHBoxLayout()
        self.btn_validate = QPushButton("✅  Valider les données / تحقق")
        self.btn_validate.setEnabled(False)
        self.btn_validate.setStyleSheet(self._btn_style(colors.WARNING))
        self.btn_validate.clicked.connect(self._run_validation)
        btn_row.addWidget(self.btn_validate)

        self.btn_import = QPushButton("📥  Importer / استيراد")
        self.btn_import.setEnabled(False)
        self.btn_import.setStyleSheet(self._btn_style(colors.SUCCESS))
        self.btn_import.clicked.connect(self._run_import)
        btn_row.addWidget(self.btn_import)

        btn_row.addStretch()

        self.btn_template = QPushButton("⬇️  Télécharger modèle / تحميل نموذج")
        self.btn_template.setStyleSheet(self._btn_style(colors.SECONDARY))
        self.btn_template.clicked.connect(self._download_template)
        btn_row.addWidget(self.btn_template)

        btn_close = QPushButton("✖  Fermer / إغلاق")
        btn_close.setStyleSheet(self._btn_style(colors.DANGER))
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)

        root.addLayout(btn_row)

    # ---------------------------------------------------------------- Data
    def _load_classes_and_years(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = ImportWizardRepository(conn)
                for yid, label in repo.list_academic_years():
                    self.combo_year.addItem(label, yid)
                for cid, cname in repo.list_classes():
                    self.combo_class.addItem(cname, cid)
        except Exception as e:
            AppLogger.error("ImportWizard", f"Chargement classes/années: {e}")

    # ---------------------------------------------------------------- File
    def _browse_file(self):
        filters = "Fichiers Excel/CSV (*.xlsx *.csv);;Excel (*.xlsx);;CSV (*.csv)"
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner le fichier", "", filters)
        if not path:
            return
        self.lbl_file.setText(os.path.basename(path))
        self._load_file(path)

    def _load_file(self, path: str):
        self._raw_headers.clear()
        self._raw_rows.clear()
        self.log_text.clear()
        self.btn_validate.setEnabled(False)
        self.btn_import.setEnabled(False)

        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".xlsx":
                if not OPENPYXL_AVAILABLE:
                    QMessageBox.critical(self, "Erreur", "openpyxl non installé. Installez-le via pip.")
                    return
                wb = openpyxl.load_workbook(path, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    self._log("⚠️ Fichier vide.")
                    return
                self._raw_headers = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(rows[0])]
                self._raw_rows    = [list(r) for r in rows[1:] if any(c is not None for c in r)]
            elif ext == ".csv":
                with open(path, encoding="utf-8-sig", newline="") as f:
                    reader = csv.reader(f)
                    all_rows = list(reader)
                if not all_rows:
                    self._log("⚠️ Fichier vide.")
                    return
                self._raw_headers = all_rows[0]
                self._raw_rows    = [r for r in all_rows[1:] if any(c.strip() for c in r)]
            else:
                self._log("❌ Format non supporté.")
                return
        except Exception as e:
            self._log(f"❌ Erreur de lecture: {e}")
            return

        self._build_mapping_ui()
        self._fill_preview()
        self.btn_validate.setEnabled(bool(self._raw_rows))
        self._log(f"✅ Fichier chargé: {len(self._raw_rows)} lignes de données, {len(self._raw_headers)} colonnes.")

    # ---------------------------------------------------------------- Mapping UI
    def _build_mapping_ui(self):
        # إزالة العناصر السابقة
        while self.mapping_layout.count():
            item = self.mapping_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._mapping_combos.clear()

        colors = ThemeManager.get_colors()
        for col_idx, header in enumerate(self._raw_headers):
            vbox = QVBoxLayout()
            lbl = QLabel(header)
            lbl.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 11px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMaximumWidth(160)

            cmb = QComboBox()
            cmb.setMaximumWidth(160)
            cmb.setStyleSheet(self._combo_style(colors))
            for key, label in STUDENT_FIELDS:
                cmb.addItem(label, key)

            # تخمين تلقائي بناءً على اسم الرأس
            auto = self._guess_field(header)
            if auto in FIELD_KEYS:
                cmb.setCurrentIndex(FIELD_KEYS.index(auto))

            vbox.addWidget(lbl)
            vbox.addWidget(cmb)
            container = QWidget()
            container.setLayout(vbox)
            self.mapping_layout.addWidget(container)
            self._mapping_combos.append(cmb)

        self.mapping_layout.addStretch()

    def _guess_field(self, header: str) -> str:
        """تخمين تلقائي للحقل بناءً على اسم العمود"""
        h = header.strip().lower()
        mapping = {
            "prenom": "first_name_fr",  "prénom": "first_name_fr",
            "first_name": "first_name_fr", "nom": "last_name_fr",
            "last_name": "last_name_fr",   "الاسم الأول": "first_name_ar",
            "اسم العائلة": "last_name_ar", "naissance": "birth_date",
            "birth": "birth_date",         "nais": "birth_date",
            "lieu": "birth_place",         "sexe": "gender",
            "genre": "gender",             "gender": "gender",
            "adresse": "address",          "address": "address",
            "parent": "parent_name",       "tuteur": "parent_name",
            "phone": "parent_phone",       "tel": "parent_phone",
            "email": "parent_email",       "mail": "parent_email",
        }
        for key, field in mapping.items():
            if key in h:
                return field
        return ""

    # ---------------------------------------------------------------- Preview
    def _fill_preview(self):
        self.preview_table.clear()
        if not self._raw_headers:
            return
        self.preview_table.setColumnCount(len(self._raw_headers))
        self.preview_table.setHorizontalHeaderLabels(self._raw_headers)
        preview = self._raw_rows[:10]
        self.preview_table.setRowCount(len(preview))
        for r, row in enumerate(preview):
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "")
                self.preview_table.setItem(r, c, item)

    # ---------------------------------------------------------------- Validation
    def _run_validation(self):
        self._validated_rows.clear()
        self.btn_import.setEnabled(False)
        self.log_text.clear()

        errors_found = 0
        for row_idx, raw_row in enumerate(self._raw_rows):
            data = self._map_row(raw_row)
            data["gender"] = _normalize_gender(data.get("gender", ""))
            if data.get("birth_date"):
                data["birth_date"] = _parse_date(data["birth_date"])
                # التحقق من التاريخ لـ validators
                try:
                    from datetime import date as _date
                    data["_birth_date_obj"] = datetime.strptime(
                        data["birth_date"], "%Y-%m-%d"
                    ).date() if data["birth_date"] else None
                except (ValueError, TypeError):
                    data["_birth_date_obj"] = None

            # validators.py يتوقع مفتاح 'birth_date' كـ date object
            validate_data = dict(data)
            if data.get("_birth_date_obj"):
                validate_data["birth_date"] = data["_birth_date_obj"]
            validate_data.pop("_birth_date_obj", None)

            errs = validate_student(validate_data)
            if errs:
                errors_found += 1
                self._log(
                    f"❌  Ligne {row_idx + 2}: {format_errors(errs)}",
                    color="#EF4444"
                )
            else:
                self._validated_rows.append(data)

        valid = len(self._validated_rows)
        total = len(self._raw_rows)

        if errors_found:
            self._log(f"\n⚠️  {errors_found} ligne(s) invalide(s) — {valid} valide(s) sur {total}.")
        else:
            self._log(f"✅  Toutes les {valid} lignes sont valides.")

        if valid > 0:
            self.btn_import.setEnabled(True)

    def _map_row(self, raw_row: list) -> dict:
        """تحويل صف خام إلى dict بناءً على تعيين الأعمدة"""
        data = {}
        for col_idx, cmb in enumerate(self._mapping_combos):
            field_key = cmb.currentData()
            if not field_key:
                continue
            val = raw_row[col_idx] if col_idx < len(raw_row) else None
            data[field_key] = str(val).strip() if val is not None else ""
        return data

    # ---------------------------------------------------------------- Import
    def _run_import(self):
        class_id = self.combo_class.currentData()
        year_id  = self.combo_year.currentData()

        if not class_id or not year_id:
            QMessageBox.warning(self, "Sélection manquante",
                                "Veuillez sélectionner une classe et une année scolaire.")
            return
        if not self._validated_rows:
            QMessageBox.warning(self, "Pas de données", "Aucune ligne valide à importer.")
            return

        confirm = QMessageBox.question(
            self, "Confirmation",
            f"Importer {len(self._validated_rows)} élève(s) dans la classe sélectionnée ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.btn_import.setEnabled(False)
        self.btn_validate.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        self._worker = ImportWorker(self._validated_rows, class_id, year_id, self.actor)
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.row_result.connect(self._on_row_result)
        self._worker.finished_sig.connect(self._on_import_finished)
        self._worker.start()

    def _on_row_result(self, idx: int, success: bool, msg: str):
        row_data = self._validated_rows[idx] if idx < len(self._validated_rows) else {}
        name = f"{row_data.get('first_name_fr', '')} {row_data.get('last_name_fr', '')}".strip()
        if success:
            self._log(f"✅  [{idx + 1}] {name} — {msg}", color="#10B981")
        else:
            self._log(f"❌  [{idx + 1}] {name} — {msg}", color="#EF4444")

    def _on_import_finished(self, imported: int, failed: int):
        self.progress_bar.setValue(100)
        self._log(
            f"\n🏁  Importation terminée: {imported} réussi(s), {failed} échoué(s).",
            color="#3B82F6"
        )
        self.btn_validate.setEnabled(True)
        AppLogger.info("ImportWizard", f"Import terminé: {imported} ok, {failed} erreurs")
        if imported > 0:
            QMessageBox.information(
                self, "Importation terminée",
                f"✅  {imported} élève(s) importé(s) avec succès.\n"
                + (f"⚠️  {failed} ligne(s) en erreur." if failed else "")
            )

    # ---------------------------------------------------------------- Template
    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le modèle", "modele_import_eleves.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        headers = [lbl for key, lbl in STUDENT_FIELDS if key]
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow([
                    "Ahmed", "Diallo", "أحمد", "ديالو",
                    "2010-05-15", "Dakar", "M", "Rue 10 Dakar",
                    "Moussa Diallo", "771234567", "", ""
                ])
            QMessageBox.information(self, "Modèle enregistré",
                                    f"Modèle sauvegardé:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ---------------------------------------------------------------- Helpers
    def _log(self, msg: str, color: str = ""):
        if color:
            self.log_text.append(f'<span style="color:{color};">{msg}</span>')
        else:
            self.log_text.append(msg)

    @staticmethod
    def _btn_style(color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color}; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
            QPushButton:disabled {{ background-color: #94A3B8; }}
        """

    @staticmethod
    def _combo_style(colors) -> str:
        return f"""
            QComboBox {{
                background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY};
                border: 1px solid {colors.BORDER}; border-radius: 5px; padding: 4px 8px;
            }}
        """
