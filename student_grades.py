import os
import sys

from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from pdf_report_style import apply_table_body_style, apply_table_header_style, set_zebra_row_fill
from print_export_service import get_report_output_mode, output_pdf
from repositories.finance_repo import FinanceRepository
from repositories.grades_repo import GradesRepository
from repositories.student_repo import StudentRepository
from ui_styles import ModuleHeaderWidget, ThemeManager, get_module_caps, get_tabs_style

GRADES_SHEET_OUTPUT_MODE = get_report_output_mode("grades_sheet_mode", "print")

from pdf_helpers import ARABIC_SUPPORT
from pdf_helpers import prepare_pdf_text as _prepare_pdf_text
from pdf_helpers import sanitize_latin as _sanitize_latin
from pdf_helpers import setup_pdf_arabic_font
from ui_components import card_frame, style_table, styled_combo

# --- فئة تقارير PDF الرسمية ---


class GradesSheetPDF(FPDF):
    def __init__(self, title_doc="FEUILLE DE NOTES"):
        super().__init__()
        self.title_doc = title_doc
        self.school_info = None
        self.font_name = "Helvetica"
        self.arabic_font_ready = False
        if ARABIC_SUPPORT:
            setup_pdf_arabic_font(self)
            self.font_name = "ArabicFont"
            self.arabic_font_ready = True

    def set_school_info(self, info):
        self.school_info = info

    def sanitize(self, text):
        if self.arabic_font_ready:
            return _prepare_pdf_text(text)
        return _sanitize_latin(text)

    def header(self):
        left_x, left_y = 10, 5
        self.set_xy(left_x, left_y)
        self.set_font(self.font_name, '', 8)
        if self.school_info and len(self.school_info) > 7:
            republic = self.sanitize(self.school_info[1])
            self.cell(80, 3, republic, 0, 1, 'L')
            ia_text = self.sanitize(self.school_info[2])
            self.cell(80, 3, ia_text, 0, 1, 'L')
            ief_text = self.sanitize(self.school_info[3])
            self.cell(80, 3, ief_text, 0, 1, 'L')
            school_name = self.sanitize(self.school_info[4])
            self.cell(80, 3, school_name, 0, 1, 'L')
            auth_text = self.sanitize(self.school_info[5])
            self.cell(80, 3, f"Auto N: {auth_text}", 0, 1, 'L')
            addr_text = self.sanitize(self.school_info[6])
            self.cell(80, 3, f"Lieu: {addr_text}", 0, 1, 'L')
            phone_text = self.sanitize(self.school_info[7])
            self.cell(80, 3, f"Tel: {phone_text}", 0, 1, 'L')

        right_x = 175
        logo_path = self.school_info[8] if self.school_info and len(self.school_info) > 8 else None
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=right_x, y=left_y, w=20, h=22)
            except Exception:
                pass

        self.set_xy(right_x, left_y + 22)
        self.set_y(self.get_y() + 2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

        title_style = '' if self.arabic_font_ready else 'B'
        self.set_font(self.font_name, title_style, 12)
        self.set_text_color(44, 62, 80)
        self.cell(0, 8, self.title_doc, 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


class StudentGradesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Notes / إدارة العلامات")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_classes(self.combo_class)
        self.load_classes(self.combo_view_class)
        self.on_view_class_changed()
        self._load_kpi_stats()

    # ===== إضافة دالة جلب السنة النشطة =====
    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return StudentRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "student_grades")
        # btn_save يُنشأ في setup_entry_tab → قد لا يكون موجوداً بعد في هذه المرحلة
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(caps["can_write"])
            self.btn_save.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. En-tête unifié
        header = ModuleHeaderWidget(
            icon="📝",
            title="GESTION DES NOTES",
            subtitle="إدارة العلامات والاختبارات",
        )
        self.main_layout.addWidget(header)
        self._stat_entries = header.add_stat("📊", "Notes Saisies", "—", "#3B82F6")
        self._stat_avg = header.add_stat("⭐", "Moyenne Générale", "—", "#22C55E")
        self._stat_low = header.add_stat("⚠️", "Sous Moyenne", "—", "#EF4444")
        self._stat_subjects = header.add_stat("📖", "Matières", "—", "#8B5CF6")

        # 2. KPI Cards

        # 3. Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())

        self.setup_entry_tab()
        self.setup_view_tab()

        self.main_layout.addWidget(self.tabs)

    def _load_kpi_stats(self):
        """Charge les statistiques globales des notes dans les KPI Cards."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Total notes saisies
                cursor.execute("SELECT COUNT(*) FROM Grades")
                total_entries = cursor.fetchone()[0] or 0
                # Moyenne générale
                cursor.execute("SELECT AVG(score) FROM Grades WHERE score IS NOT NULL")
                avg_row = cursor.fetchone()
                avg_score = avg_row[0] if avg_row and avg_row[0] is not None else None
                # Étudiants sous la moyenne (score < 10)
                cursor.execute("SELECT COUNT(DISTINCT student_id) FROM Grades WHERE score IS NOT NULL AND score < 10")
                low_count = cursor.fetchone()[0] or 0
                # Nombre de matières
                cursor.execute("SELECT COUNT(*) FROM Subjects")
                subj_count = cursor.fetchone()[0] or 0

            self._stat_entries.set_value(f"{total_entries:,}")
            self._stat_avg.set_value(f"{avg_score:.1f}" if avg_score is not None else "—")
            self._stat_low.set_value(str(low_count))
            self._stat_subjects.set_value(str(subj_count))
        except Exception as e:
            AppLogger.error("StudentGradesWindow", f"Erreur KPI stats: {e}")

    def sanitize_filename(self, text):
        if not text:
            return ""
        cleaned = str(text).strip().replace(" ", "_")
        return "".join(ch for ch in cleaned if ch.isalnum() or ch in "-_")

    # ---------------------------------------------------------
    # TAB 1: Saisie (الإدخال)
    # ---------------------------------------------------------
    def setup_entry_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        filter_card = card_frame()
        vlay_f = QVBoxLayout(filter_card)
        vlay_f.setContentsMargins(12, 10, 12, 10)
        vlay_f.setSpacing(8)

        self.combo_class = styled_combo(min_height=32)
        self.combo_class.currentIndexChanged.connect(self.on_class_changed_entry)

        self.combo_subject = styled_combo(min_height=32)
        self.combo_subject.addItem("- Matière -", None)

        self.combo_period = styled_combo(min_height=32)
        self.combo_period.addItem("- Période -", None)
        self.combo_period.currentIndexChanged.connect(self.load_assessments_entry)

        self.combo_assessment = styled_combo(min_height=32)
        self.combo_assessment.addItem("- Évaluation -", None)

        btn_load = QPushButton("📥 Charger / تحميل")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors()
        btn_load.setFixedHeight(32)
        btn_load.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; font-weight: bold; font-size:11px;"
            f" padding: 4px 16px; border-radius: 7px; border: none; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_load.clicked.connect(self.load_grading_sheet)

        row1_g = QHBoxLayout()
        row1_g.setSpacing(8)
        row1_g.addWidget(self.combo_class, 1)
        row1_g.addWidget(self.combo_subject, 1)

        row2_g = QHBoxLayout()
        row2_g.setSpacing(8)
        row2_g.addWidget(self.combo_period, 1)
        row2_g.addWidget(self.combo_assessment, 1)
        row2_g.addWidget(btn_load)

        vlay_f.addLayout(row1_g)
        vlay_f.addLayout(row2_g)

        layout.addWidget(filter_card)

        self.table_grades = QTableWidget()
        style_table(self.table_grades)
        self.table_grades.setColumnCount(5)
        self.table_grades.setHorizontalHeaderLabels(["ID", "Nom (FR)", "Nom (AR)", "Note", "Obs"])
        self.table_grades.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_grades.verticalHeader().setDefaultSectionSize(44)
        layout.addWidget(self.table_grades)

        btn_print_blank = QPushButton("🖨️ Feuille Vierge")
        btn_print_blank.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print_blank.setFixedHeight(38)
        btn_print_blank.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SECONDARY}, stop:1 #0284C7); color: white; font-weight: bold; font-size:11px; padding: 4px 14px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.PRIMARY_HOVER}; }}"
        )
        btn_print_blank.clicked.connect(self.print_sheet)

        self.btn_save = QPushButton("💾 Enregistrer")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(38)
        self.btn_save.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {colors.SUCCESS}, stop:1 #16A34A); color: white; font-weight: bold; font-size:11px; padding: 4px 14px; border-radius: 8px; border: none; }} QPushButton:hover {{ background: {colors.SUCCESS_HOVER}; }}"
        )
        self.btn_save.clicked.connect(self.save_grades)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        action_layout.addWidget(btn_print_blank)
        action_layout.addWidget(self.btn_save)
        layout.addLayout(action_layout)

        self.tabs.addTab(tab, "  📝 Saisie / الإدخال  ")

    def setup_view_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        search_card = card_frame()
        slayout = QHBoxLayout(search_card)
        slayout.setContentsMargins(12, 10, 12, 10)
        slayout.setSpacing(8)

        self.combo_view_class = styled_combo(min_height=32)
        self.combo_view_class.addItem("Toutes les classes", None)
        self.combo_view_class.currentIndexChanged.connect(self.on_view_class_changed)

        self.combo_view_period = styled_combo(min_height=32)
        self.combo_view_period.addItem("Toutes les périodes", None)
        self.combo_view_period.currentIndexChanged.connect(self.search_grades)

        self.txt_search_student = QLineEdit()
        self.txt_search_student.setPlaceholderText("Nom de l'etudiant...")
        self.txt_search_student.setFixedHeight(32)
        colors = ThemeManager.get_colors()
        self.txt_search_student.setStyleSheet(
            f"QLineEdit {{ padding: 4px 10px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 7px; background-color: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-size: 11px; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}"
        )

        btn_search = QPushButton("🔍 Rechercher")
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setFixedHeight(32)
        btn_search.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {colors.PRIMARY}; font-weight: bold; font-size:11px; padding: 4px 14px; border-radius: 7px; border: 1.5px solid {colors.PRIMARY}; }} QPushButton:hover {{ background-color: {colors.PRIMARY_LIGHT}; }}"
        )
        btn_search.clicked.connect(self.search_grades)

        slayout.addWidget(self.combo_view_class, 1)
        slayout.addWidget(self.combo_view_period, 1)
        slayout.addWidget(self.txt_search_student, 2)
        slayout.addWidget(btn_search)

        layout.addWidget(search_card)

        self.table_view = QTableWidget()
        style_table(self.table_view)
        self.table_view.setColumnCount(7)
        self.table_view.setHorizontalHeaderLabels(["Date", "Classe", "Eleve", "Matiere", "Eval", "Note", "Obs"])
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_view.verticalHeader().setDefaultSectionSize(32)
        layout.addWidget(self.table_view)

        self.tabs.addTab(tab, "  👁️ Consultation & Historique / الأرشيف  ")

    # ---------------------------------------------------------
    # Logic methods
    # ---------------------------------------------------------
    def load_classes(self, combo=None):
        if combo is None:
            # Called from refresh — reload all class combos
            self.load_classes(self.combo_class)
            self.load_classes(self.combo_view_class)
            return
        combo.clear()
        combo.addItem("- Choisir -", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for c in GradesRepository(conn).list_classes():
                    combo.addItem(c[1], c[0])
        except Exception as e:
            AppLogger.error("StudentGrades", f"Error loading classes: {e}")

    def load_periods(self, combo):
        try:
            active_year = self.get_active_year_id()
            if active_year == -1:
                return
            db = DatabaseManager()
            with db.get_connection() as conn:
                seen = set()
                for p in GradesRepository(conn).list_periods_for_year(active_year):
                    if p[1] not in seen:
                        combo.addItem(p[1], p[0])
                        seen.add(p[1])
        except Exception:
            pass

    def on_view_class_changed(self):
        class_id = self.combo_view_class.currentData()
        self.combo_view_period.blockSignals(True)
        self.combo_view_period.clear()
        self.combo_view_period.addItem("Toutes les périodes", None)

        try:
            active_year = self.get_active_year_id()
            if active_year == -1:
                return
            db = DatabaseManager()
            with db.get_connection() as conn:
                periods = (
                    GradesRepository(conn).list_periods_for_class_year(class_id, active_year)
                    if class_id
                    else GradesRepository(conn).list_periods_for_year(active_year)
                )
            for period_id, period_name in periods:
                self.combo_view_period.addItem(period_name, period_id)
        except Exception:
            pass
        finally:
            self.combo_view_period.blockSignals(False)

    def on_class_changed_entry(self):
        class_id = self.combo_class.currentData()
        self.combo_subject.clear()
        self.combo_subject.addItem("- Matière -", None)
        self.combo_period.clear()
        self.combo_period.addItem("- Période -", None)
        if not class_id:
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                subjects = repo.get_class_subjects(class_id)
                if not subjects:
                    return

                for s in subjects:
                    self.combo_subject.addItem(f"{s[1]} (Coef: {s[3]})", s[0])

                for p in repo.list_periods_for_class_year(class_id, active_year):
                    self.combo_period.addItem(p[1], p[0])
        except Exception as e:
            AppLogger.error("StudentGrades", f"Error class changed: {e}")

    def load_assessments_entry(self):
        period_id = self.combo_period.currentData()
        self.combo_assessment.clear()
        self.combo_assessment.addItem("- Évaluation -", None)
        if not period_id:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for a in GradesRepository(conn).list_assessments_for_period(period_id):
                    self.combo_assessment.addItem(a[1], a[0])
        except Exception:
            pass

    # ===== جلب الطلاب باستخدام جدول التسجيل SCN =====

    def load_grading_sheet(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()

        if not all([class_id, subject_id, assess_id]):
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner la classe, la matière et l'évaluation.")
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            QMessageBox.warning(self, "Attention", "Aucune année scolaire active n'a été trouvée.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                max_score = repo.get_max_score_for_class(class_id)
                self.table_grades.horizontalHeaderItem(3).setText(f"Note /{int(max_score)}")
                rows = repo.load_grading_sheet(class_id, subject_id, assess_id, active_year)

                self.table_grades.setRowCount(0)
                colors = ThemeManager.get_colors()

                for r in rows:
                    idx = self.table_grades.rowCount()
                    self.table_grades.insertRow(idx)

                    id_item = QTableWidgetItem(str(r[0]))
                    id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 0, id_item)

                    item_fr = QTableWidgetItem(r[1])
                    item_fr.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 1, item_fr)

                    item_ar = QTableWidgetItem(r[2])
                    item_ar.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 2, item_ar)

                    spin = QDoubleSpinBox()
                    spin.setRange(0, max_score)
                    spin.setSingleStep(0.25)
                    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    spin.setStyleSheet(
                        f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};"
                    )
                    if r[3] is not None:
                        spin.setValue(r[3])
                    self.table_grades.setCellWidget(idx, 3, spin)

                    self.table_grades.setItem(idx, 4, QTableWidgetItem(r[4] or ""))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement : {e}")

    def save_grades(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()

        if not all([class_id, subject_id, assess_id]):
            return

        active_year = self.get_active_year_id()
        if active_year == -1:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                today = QDate.currentDate().toString("yyyy-MM-dd")
                for row in range(self.table_grades.rowCount()):
                    sid = int(self.table_grades.item(row, 0).text())
                    score_widget = self.table_grades.cellWidget(row, 3)
                    score = score_widget.value() if score_widget else 0.0
                    obs = self.table_grades.item(row, 4).text()
                    repo.upsert_grade(sid, subject_id, assess_id, active_year, score, obs, today)
                conn.commit()
            QMessageBox.information(self, "Info", "Notes enregistrées avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement : {e}")

    def search_grades(self):
        class_id = self.combo_view_class.currentData()
        period_id = self.combo_view_period.currentData()
        student_name = self.txt_search_student.text().strip()
        active_year = self.get_active_year_id()

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = GradesRepository(conn).search_grades(
                    active_year,
                    class_id=class_id,
                    period_id=period_id,
                    student_name=student_name or None,
                )

                self.table_view.setRowCount(0)
                for r in rows:
                    idx = self.table_view.rowCount()
                    self.table_view.insertRow(idx)
                    for c, val in enumerate(r):
                        self.table_view.setItem(idx, c, QTableWidgetItem(str(val if val is not None else "-")))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de recherche : {e}")

    def print_sheet(self):
        class_id = self.combo_class.currentData()
        subject_id = self.combo_subject.currentData()
        assess_id = self.combo_assessment.currentData()
        active_year = self.get_active_year_id()

        if not all([class_id, subject_id, assess_id]):
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner la classe, la matière et l'évaluation.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = GradesRepository(conn)
                try:
                    school_info = FinanceRepository(conn).get_school_info()
                except Exception:
                    school_info = None
                cls_txt = repo.get_class_label(class_id)
                sub_txt = repo.get_subject_label(subject_id)
                eval_txt = repo.get_assessment_label(assess_id)
                max_score = repo.get_max_score_for_class(class_id)
                rows = repo.get_students_for_class_year(class_id, active_year)

            file_stub = f"Feuille_Notes_{self.sanitize_filename(cls_txt)}_{self.sanitize_filename(sub_txt)}_{self.sanitize_filename(eval_txt)}"

            if self.table_grades.rowCount() == 0:
                self.table_grades.horizontalHeaderItem(3).setText(f"Note /{int(max_score)}")
                self.table_grades.setRowCount(0)
                colors = ThemeManager.get_colors()

                for r in rows:
                    idx = self.table_grades.rowCount()
                    self.table_grades.insertRow(idx)

                    id_item = QTableWidgetItem(str(r[0]))
                    id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 0, id_item)

                    item_fr = QTableWidgetItem(r[1])
                    item_fr.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 1, item_fr)

                    item_ar = QTableWidgetItem(r[2])
                    item_ar.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    self.table_grades.setItem(idx, 2, item_ar)

                    spin = QDoubleSpinBox()
                    spin.setRange(0, max_score)
                    spin.setSingleStep(0.25)
                    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    spin.setStyleSheet(
                        f"background: {colors.INPUT_BG}; border: 1px solid {colors.BORDER}; color: {colors.TEXT_PRIMARY};"
                    )
                    self.table_grades.setCellWidget(idx, 3, spin)

                    self.table_grades.setItem(idx, 4, QTableWidgetItem(""))

            pdf = GradesSheetPDF()
            pdf.set_school_info(school_info)
            pdf.add_page()

            pdf.set_font(pdf.font_name, '', 11)
            cls_txt_pdf = pdf.sanitize(self.combo_class.currentText())
            sub_txt_pdf = pdf.sanitize(self.combo_subject.currentText())
            eval_txt_pdf = pdf.sanitize(self.combo_assessment.currentText())

            pdf.cell(0, 7, f"Classe: {cls_txt_pdf}", 0, 1)
            pdf.cell(0, 7, f"Matiere: {sub_txt_pdf}", 0, 1)
            pdf.cell(0, 7, f"Evaluation: {eval_txt_pdf}", 0, 1)
            pdf.ln(5)

            apply_table_header_style(pdf, pdf.font_name, 10)
            pdf.cell(15, 8, "ID", 1, 0, 'C', True)
            pdf.cell(80, 8, "Nom et Prenom", 1, 0, 'C', True)
            pdf.cell(30, 8, "Note", 1, 0, 'C', True)
            pdf.cell(65, 8, "Observation", 1, 1, 'C', True)

            apply_table_body_style(pdf, pdf.font_name, 10)
            for row in range(self.table_grades.rowCount()):
                sid = self.table_grades.item(row, 0).text()
                name = self.table_grades.item(row, 1).text()
                safe_name = pdf.sanitize(name)
                set_zebra_row_fill(pdf, row)

                pdf.cell(15, 8, sid, 1, 0, 'C', True)
                pdf.cell(80, 8, safe_name, 1, 0, 'L', True)
                pdf.cell(30, 8, "", 1, 0, 'C', True)
                pdf.cell(65, 8, "", 1, 1, 'L', True)

            output_pdf(
                pdf,
                self,
                f"{file_stub}.pdf",
                mode=GRADES_SHEET_OUTPUT_MODE,
                dialog_title="Save PDF",
                success_save_message="PDF généré.",
                success_print_message="Feuille envoyée à l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentGradesWindow()
    window.show()
    sys.exit(app.exec())
