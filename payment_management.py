import sys
from datetime import datetime

# FIX 3: Removed `import psycopg2` — never referenced in this file.
# FIX 4: Removed `import os` — no os.* calls exist anywhere in this file.
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (  # FIX 5: Removed QComboBox — only used in the dead styled_combo() instance method below.
    QApplication,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager
from pdf_report_style import apply_grades_sheet_header
from print_export_service import get_report_output_mode, output_pdf
from repositories.finance_repo import FinanceRepository
from ui_components import card_frame, compact_icon_btn, style_table, styled_combo
from ui_styles import Colors, ModuleHeaderWidget, ThemeManager, get_module_caps

STUDENT_DUES_REPORT_OUTPUT_MODE = get_report_output_mode("student_dues_report_mode", "save")


class StudentDuesReportPDF(FPDF):
    def sanitize(self, text):
        if text is None:
            return ""
        value = str(text)
        return value.encode("latin-1", "ignore").decode("latin-1")


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------


class AddDueDialog(QDialog):
    """Popup pour ajouter une facture personnalisée à un élève."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle Facture / فاتورة جديدة")
        self.setMinimumWidth(460)
        self.setModal(True)
        ThemeManager.apply_theme(self)
        self._build_ui()

    def _build_ui(self):
        colors = ThemeManager.get_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("➕ Nouvelle Facture")
        lbl_title.setStyleSheet(f"font-size:16px; font-weight:700; color:{colors.TEXT_PRIMARY};")
        layout.addWidget(lbl_title)

        # Description
        layout.addWidget(QLabel("Description / وصف الرسوم:"))
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ex: Frais de Transport")
        self.txt_desc.setMinimumHeight(42)
        self.txt_desc.setStyleSheet(
            f"QLineEdit {{ padding:9px 13px; border:1.5px solid {colors.INPUT_BORDER};"
            f" border-radius:8px; background:{colors.INPUT_BG}; color:{colors.TEXT_PRIMARY}; }}"
            f"QLineEdit:focus {{ border:2px solid {colors.BORDER_FOCUS}; }}"
        )
        layout.addWidget(self.txt_desc)

        # Amount
        layout.addWidget(QLabel("Montant (FCFA) / المبلغ:"))
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 10_000_000)
        self.spin_amount.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_amount.setMinimumHeight(42)
        self.spin_amount.setStyleSheet(
            f"QDoubleSpinBox {{ padding:9px 13px; border:1.5px solid {colors.INPUT_BORDER};"
            f" border-radius:8px; background:{colors.INPUT_BG}; color:{colors.TEXT_PRIMARY};"
            f" font-weight:bold; }}"
        )
        layout.addWidget(self.spin_amount)

        # Due date
        layout.addWidget(QLabel("Date d'échéance / تاريخ الاستحقاق:"))
        self.date_due = QDateEdit()
        self.date_due.setCalendarPopup(True)
        self.date_due.setDisplayFormat("yyyy-MM-dd")
        self.date_due.setDate(QDate.currentDate())
        self.date_due.setMinimumHeight(42)
        self.date_due.setStyleSheet(
            f"QDateEdit {{ padding:9px 13px; border:1.5px solid {colors.INPUT_BORDER};"
            f" border-radius:8px; background:{colors.INPUT_BG}; color:{colors.TEXT_PRIMARY}; }}"
            f"QDateEdit:focus {{ border:2px solid {colors.BORDER_FOCUS}; }}"
        )
        layout.addWidget(self.date_due)

        layout.addSpacing(6)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("✕ Annuler")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setMinimumHeight(42)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1.5px solid {colors.BORDER};"
            f" color:{colors.TEXT_SECONDARY}; font-weight:700; border-radius:7px; padding:6px 16px; }}"
            f"QPushButton:hover {{ background:{colors.BG_MAIN}; }}"
        )
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("✔ Enregistrer")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setMinimumHeight(42)
        self.btn_save.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {colors.SUCCESS},stop:1 #16A34A);"
            f" color:white; font-weight:700; border-radius:7px; border:none; padding:6px 16px; }}"
            f"QPushButton:hover {{ background:{colors.SUCCESS_HOVER}; }}"
            f"QPushButton:disabled {{ background:{colors.BG_MAIN}; color:{colors.TEXT_SECONDARY}; }}"
        )
        self.btn_save.clicked.connect(self.accept)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

    def get_values(self):
        return {
            "description": self.txt_desc.text().strip(),
            "amount": self.spin_amount.value(),
            "due_date": self.date_due.date().toString("yyyy-MM-dd"),
        }


class DiscountDialog(QDialog):
    """Popup pour appliquer une remise à une facture existante."""

    def __init__(self, due_id, description, original_amount, parent=None):
        super().__init__(parent)
        self.due_id = due_id
        self.original_amount = original_amount
        self.setWindowTitle("Appliquer une Remise / تطبيق خصم")
        self.setMinimumWidth(420)
        self.setModal(True)
        ThemeManager.apply_theme(self)
        self._build_ui(description, original_amount)

    def _build_ui(self, description, original_amount):
        colors = ThemeManager.get_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("🎁 Appliquer une Remise")
        lbl_title.setStyleSheet(f"font-size:16px; font-weight:700; color:{colors.TEXT_PRIMARY};")
        layout.addWidget(lbl_title)

        # Due info card
        info_frame = QFrame()
        info_frame.setStyleSheet(f"QFrame {{ background:{colors.PRIMARY_LIGHT}; border-radius:8px; border:none; }}")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        lbl_info = QLabel(f"📄 {description}\nMontant original: {original_amount:,.0f} FCFA")
        lbl_info.setStyleSheet(f"color:{colors.TEXT_PRIMARY}; font-weight:600;")
        lbl_info.setWordWrap(True)
        info_layout.addWidget(lbl_info)
        layout.addWidget(info_frame)

        # Discount amount
        layout.addWidget(QLabel("Montant de la remise / قيمة الخصم:"))
        self.spin_discount = QDoubleSpinBox()
        self.spin_discount.setRange(0, original_amount)
        self.spin_discount.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_discount.setMinimumHeight(42)
        self.spin_discount.setStyleSheet(
            f"QDoubleSpinBox {{ padding:9px 13px; border:1.5px solid {colors.INPUT_BORDER};"
            f" border-radius:8px; background:{colors.INPUT_BG}; color:{colors.TEXT_PRIMARY};"
            f" font-weight:bold; }}"
        )
        self.spin_discount.valueChanged.connect(self._update_net_label)
        layout.addWidget(self.spin_discount)

        self.lbl_net = QLabel(f"Montant net: {original_amount:,.0f} FCFA")
        self.lbl_net.setStyleSheet(f"color:{colors.SUCCESS}; font-weight:700; font-size:13px;")
        layout.addWidget(self.lbl_net)

        layout.addSpacing(6)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("✕ Annuler")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setMinimumHeight(42)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1.5px solid {colors.BORDER};"
            f" color:{colors.TEXT_SECONDARY}; font-weight:700; border-radius:7px; padding:6px 16px; }}"
            f"QPushButton:hover {{ background:{colors.BG_MAIN}; }}"
        )
        btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton("✔ Appliquer")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setMinimumHeight(42)
        self.btn_apply.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {colors.PRIMARY},stop:1 {colors.PRIMARY_HOVER});"
            f" color:white; font-weight:700; border-radius:7px; border:none; padding:6px 16px; }}"
            f"QPushButton:hover {{ background:{colors.PRIMARY_DARK}; }}"
        )
        self.btn_apply.clicked.connect(self.accept)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_apply)
        layout.addLayout(btn_row)

    def _update_net_label(self, discount_value):
        net = self.original_amount - discount_value
        self.lbl_net.setText(f"Montant net: {net:,.0f} FCFA")

    def get_discount(self):
        return self.spin_discount.value()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------


class StudentDuesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Factures / إدارة الفواتير والمطالبات")
        self.setMinimumSize(1100, 700)
        self._ensure_student_dues_schema()
        ThemeManager.apply_theme(self)
        self.init_ui()
        self.load_classes()
        self._load_kpi_stats()

    def _ensure_student_dues_schema(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'studentdues'")
                cols = {row[0].lower() for row in cursor.fetchall()}
                if cols and "fee_description" not in cols:
                    cursor.execute("ALTER TABLE StudentDues ADD COLUMN fee_description TEXT")
                    conn.commit()
        except Exception as e:
            # FIX 6: Log schema migration errors instead of silently passing —
            # a missing column or connection failure here is invisible otherwise.
            AppLogger.error("PaymentManagement", f"Schema migration error: {e}")

    # FIX 2: Removed get_active_year_id() wrapper method — it opened its own DB
    # connection before each caller's own with-block, causing 2 connections per
    # user action. active_year is now fetched via repo inside each caller's
    # existing with db.get_connection() block.

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "student_dues")
        self.btn_add_fee.setEnabled(caps["can_write"])
        self.btn_add_fee.setVisible(caps["can_write"])
        self.btn_generate_auto.setEnabled(caps["can_write"])
        self.btn_generate_auto.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. Header with KPI stats
        header = ModuleHeaderWidget(
            icon="🧾",
            title="GESTION DES FACTURES & ENGAGEMENTS",
            subtitle="إدارة المطالبات، الفواتير، والخصومات الاستثنائية",
        )
        self._stat_total_dues = header.add_stat("📊", "Total Factures", "—", "#3B82F6")
        self._stat_paid = header.add_stat("✅", "Payées", "—", "#22C55E")
        self._stat_unpaid = header.add_stat("⏳", "En Attente", "—", "#F59E0B")
        self._stat_discounts = header.add_stat("🎁", "Remises Accordées", "—", "#8B5CF6")
        self.main_layout.addWidget(header)

        # 2. Toolbar card
        colors = ThemeManager.get_colors()
        toolbar = self.create_card()
        t_lay = QHBoxLayout(toolbar)
        t_lay.setContentsMargins(12, 8, 12, 8)
        t_lay.setSpacing(8)

        self.btn_add_fee = QPushButton("➕ Nouvelle Facture")
        self.btn_add_fee.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_fee.setFixedHeight(32)
        self.btn_add_fee.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {colors.SUCCESS},stop:1 #16A34A);"
            f" color:white; font-weight:700; border-radius:7px; border:none; font-size:12px; padding:4px 12px; }}"
            f"QPushButton:hover {{ background:{colors.SUCCESS_HOVER}; }}"
            f"QPushButton:disabled {{ background:{colors.BG_MAIN}; color:{colors.TEXT_SECONDARY}; }}"
        )
        self.btn_add_fee.clicked.connect(self.open_add_due_dialog)

        self.btn_generate_auto = QPushButton("⚙️ Générer Mensualités")
        self.btn_generate_auto.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate_auto.setFixedHeight(32)
        self.btn_generate_auto.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {colors.PRIMARY},stop:1 {colors.PRIMARY_HOVER});"
            f" color:white; font-weight:700; border-radius:7px; border:none; font-size:12px; padding:4px 12px; }}"
            f"QPushButton:hover {{ background:{colors.PRIMARY_DARK}; }}"
            f"QPushButton:disabled {{ background:{colors.BG_MAIN}; color:{colors.TEXT_SECONDARY}; }}"
        )
        self.btn_generate_auto.clicked.connect(self.generate_auto_dues)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(22)
        sep.setStyleSheet(f"background:{colors.BORDER};")

        self.combo_classes = styled_combo(min_height=32)
        self.combo_classes.setFixedWidth(200)
        self.combo_classes.currentIndexChanged.connect(self.load_students)

        self.combo_students = styled_combo(min_height=32)
        self.combo_students.setFixedWidth(350)
        self.combo_students.currentIndexChanged.connect(self.load_student_dues)

        btn_export = QPushButton("🖨️ Exporter PDF")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFixedHeight(32)
        btn_export.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            # FIX 1: Added missing comma between stop:0 and stop:1 — Qt silently
            # falls back to flat color when the comma is absent.
            f" stop:0 {colors.PRIMARY}, stop:1 {colors.PRIMARY_HOVER});"
            f" color: white; font-weight: bold; font-size:11px;"
            f" padding: 4px 14px; border-radius: 7px; border: none; }}"
            f"QPushButton:hover {{ background: {colors.PRIMARY_DARK}; }}"
        )
        btn_export.clicked.connect(self.export_student_dues_report)

        t_lay.addWidget(self.btn_add_fee)
        t_lay.addWidget(self.btn_generate_auto)
        t_lay.addWidget(sep)
        t_lay.addWidget(self.combo_classes)
        t_lay.addWidget(self.combo_students)
        t_lay.addStretch()
        t_lay.addWidget(btn_export)
        self.main_layout.addWidget(toolbar)

        # 3. Full-width table card
        table_card = self.create_card()
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(20, 16, 20, 16)
        tc_lay.setSpacing(12)

        table_title = QLabel("📄 Relevé de Compte / كشف حساب المطالبات")
        table_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        table_title.setStyleSheet(f"color:{colors.TEXT_PRIMARY};")
        tc_lay.addWidget(table_title)

        self.table_dues = QTableWidget()
        self.style_table(self.table_dues)
        self.table_dues.setColumnCount(8)
        self.table_dues.setHorizontalHeaderLabels(
            ["ID", "Description", "Date", "Montant", "Remise", "Net", "Statut", "Actions"]
        )
        self.table_dues.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tc_lay.addWidget(self.table_dues)

        self.main_layout.addWidget(table_card)

    # ================== Helper UI Methods ==================

    def create_card(self):
        return card_frame()

    # FIX 5: Removed dead styled_combo() instance method — init_ui() calls the
    # module-level styled_combo(min_height=32) imported from ui_components; this
    # instance method was never called and was shadowing the import.

    def _load_kpi_stats(self):
        """Charge les statistiques globales des factures."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM StudentDues")
                total = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(*) FROM StudentDues WHERE LOWER(status) IN ('paid', 'payé', 'paye')")
                paid = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(*) FROM StudentDues WHERE LOWER(status) NOT IN ('paid', 'payé', 'paye')")
                unpaid = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COUNT(*) FROM StudentDues WHERE discount_amount > 0")
                discounts = cursor.fetchone()[0] or 0
            self._stat_total_dues.set_value(str(total))
            self._stat_paid.set_value(str(paid))
            self._stat_unpaid.set_value(str(unpaid))
            self._stat_discounts.set_value(str(discounts))
        except Exception as e:
            AppLogger.error("PaymentManagementWindow", f"Erreur KPI stats: {e}")

    def style_table(self, table):
        style_table(table)

    # ================== Logic Methods ==================

    def load_classes(self):
        self.combo_classes.clear()
        self.combo_classes.addItem("📂 Choisir Classe", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for c in FinanceRepository(conn).list_classes():
                    self.combo_classes.addItem(str(c[1] or "-"), c[0])
        except Exception as e:
            AppLogger.error("PaymentManagement", f"Error loading classes: {e}")

    def load_students(self):
        cid = self.combo_classes.currentData()
        self.combo_students.clear()
        self.combo_students.addItem("👤 Tous les élèves", None)
        if not cid:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # FIX 2: active_year fetched inside the existing connection.
                active_year = repo.get_active_year_id()
                if not active_year or active_year == -1:
                    return
                for s in repo.list_students_by_class(cid, active_year):
                    self.combo_students.addItem((str(s[1] or "").strip() or "[Élève]"), s[0])
        except Exception as e:
            AppLogger.error("PaymentManagement", f"Error loading students: {e}")

    def load_student_dues(self):
        self.table_dues.setRowCount(0)
        sid = self.combo_students.currentData()
        if not sid:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # FIX 2: active_year fetched inside the existing connection.
                active_year = repo.get_active_year_id()
                if not active_year or active_year == -1:
                    return
                rows = repo.get_dues_for_management(sid, active_year)
                colors = ThemeManager.get_colors()

                def _to_float(value):
                    try:
                        return float(value)
                    except Exception:
                        return 0.0

                for row in rows:
                    idx = self.table_dues.rowCount()
                    self.table_dues.insertRow(idx)

                    original_amount = _to_float(row[3])
                    discount_amount = _to_float(row[4])
                    net_amount = _to_float(row[5])

                    self.table_dues.setItem(idx, 0, QTableWidgetItem(str(row[0])))
                    desc = (str(row[2] or row[1] or "-")).strip() or "-"
                    self.table_dues.setItem(idx, 1, QTableWidgetItem(desc))
                    self.table_dues.setItem(idx, 2, QTableWidgetItem(str(row[6] or "-")))
                    self.table_dues.setItem(idx, 3, QTableWidgetItem(f"{original_amount:,.0f}"))
                    self.table_dues.setItem(idx, 4, QTableWidgetItem(f"{discount_amount:,.0f}"))

                    net_item = QTableWidgetItem(f"{net_amount:,.0f}")
                    net_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                    self.table_dues.setItem(idx, 5, net_item)

                    status_txt = "✅ Réglé (مدفوع)" if row[7] else "⏳ En attente (مستحق)"
                    status_item = QTableWidgetItem(status_txt)
                    status_item.setForeground(QColor(colors.SUCCESS if row[7] else colors.WARNING))
                    self.table_dues.setItem(idx, 6, status_item)

                    container = QWidget()
                    btn_layout = QHBoxLayout(container)
                    btn_layout.setContentsMargins(2, 2, 2, 2)
                    btn_layout.setSpacing(4)
                    if not row[7]:
                        due_id = row[0]
                        btn_discount = QPushButton("🎁 Remise")
                        btn_discount.setFixedHeight(30)
                        btn_discount.setStyleSheet(
                            f"QPushButton {{ background:{colors.PRIMARY}; color:white;"
                            f" border-radius:6px; font-size:11px; font-weight:700;"
                            f" padding:2px 8px; border:none; }}"
                            f"QPushButton:hover {{ background:{colors.PRIMARY_DARK}; }}"
                        )
                        btn_discount.clicked.connect(
                            lambda ch, d_id=due_id, d_desc=desc, d_orig=original_amount: self.open_discount_dialog(
                                d_id, d_desc, d_orig
                            )
                        )
                        btn_del = QPushButton("✕ Suppr.")
                        btn_del.setFixedHeight(30)
                        btn_del.setStyleSheet(
                            f"QPushButton {{ background:{colors.DANGER}; color:white;"
                            f" border-radius:6px; font-size:11px; font-weight:700;"
                            f" padding:2px 8px; border:none; }}"
                            f"QPushButton:hover {{ background:{colors.DANGER_HOVER}; }}"
                        )
                        btn_del.clicked.connect(lambda ch, fid=row[0]: self.delete_due(fid))
                        btn_layout.addWidget(btn_discount)
                        btn_layout.addWidget(btn_del)
                    self.table_dues.setCellWidget(idx, 7, container)
        except Exception as e:
            AppLogger.error("PaymentManagement", f"Error loading dues: {e}")

    def open_add_due_dialog(self):
        sid = self.combo_students.currentData()
        if not sid:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève d'abord.")
            return
        dlg = AddDueDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            desc, amt, date_d = vals["description"], vals["amount"], vals["due_date"]
            if not desc or amt <= 0:
                QMessageBox.warning(self, "Erreur", "La description et le montant sont obligatoires.")
                return
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = FinanceRepository(conn)
                    # FIX 2: active_year fetched inside the existing connection.
                    active_year = repo.get_active_year_id()
                    if not active_year or active_year == -1:
                        return
                    repo.add_due(sid, active_year, "Custom", desc, amt, amt, date_d)
                    conn.commit()
                QMessageBox.information(self, "Succès", "Facture ajoutée avec succès.")
                self.load_student_dues()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def open_discount_dialog(self, due_id, description, original_amount):
        dlg = DiscountDialog(due_id, description, original_amount, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_discount = dlg.get_discount()
            if new_discount > original_amount:
                QMessageBox.warning(self, "Erreur", "La remise ne peut pas dépasser le montant original.")
                return
            new_net = original_amount - new_discount
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    repo = FinanceRepository(conn)
                    if repo.get_due_is_paid(due_id):
                        QMessageBox.warning(self, "Erreur", "Impossible de modifier une facture déjà payée.")
                        return
                    repo.update_due_discount(due_id, new_discount, new_net)
                    conn.commit()
                QMessageBox.information(self, "Succès", "Remise appliquée avec succès.")
                self.load_student_dues()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def delete_due(self, due_id):
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous supprimer cette facture ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    FinanceRepository(conn).delete_due(due_id)
                    conn.commit()
                self.load_student_dues()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def generate_auto_dues(self):
        cid = self.combo_classes.currentData()
        if not cid:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner une classe pour générer les factures.")
            return
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Cette action va générer les factures (Inscription et Mensualités) pour TOUS"
            " les élèves de cette classe qui n'en ont pas encore. Continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # FIX 2: active_year fetched inside the existing connection.
                active_year = repo.get_active_year_id()
                if not active_year or active_year == -1:
                    return
                reg_amt = repo.get_registration_fee(cid)
                monthly_fees = repo.get_monthly_fee_schedule(cid)
                students = repo.list_students_in_class(cid, active_year)
                generated_count = 0
                today_str = QDate.currentDate().toString("yyyy-MM-dd")
                for (sid,) in students:
                    if reg_amt > 0 and repo.count_dues_by_type(sid, active_year, "Registration") == 0:
                        repo.add_due(
                            sid, active_year, "Registration", "Frais d'inscription", reg_amt, reg_amt, today_str
                        )
                        generated_count += 1
                    for m_idx, m_name, m_amt in monthly_fees:
                        if repo.count_dues_by_type(sid, active_year, f"Month_{m_idx}") == 0:
                            due_y = datetime.now().year
                            if m_idx < 9:
                                due_y += 1
                            due_d = f"{due_y}-{m_idx:02d}-05"
                            repo.add_due(
                                sid, active_year, f"Month_{m_idx}", f"Mensualité {m_name}", m_amt, m_amt, due_d
                            )
                            generated_count += 1
                conn.commit()
            QMessageBox.information(self, "Terminé", f"Opération terminée. {generated_count} factures générées.")
            self.load_student_dues()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _slugify(self, value):
        text = (value or "").strip().replace(" ", "_")
        clean = "".join(ch for ch in text if ch.isalnum() or ch in "-_")
        return clean or "NA"

    def export_student_dues_report(self):
        student_id = self.combo_students.currentData()
        if not student_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un élève d'abord.")
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # FIX 2: active_year fetched inside the existing connection.
                active_year = repo.get_active_year_id()
                if not active_year or active_year == -1:
                    QMessageBox.warning(self, "Erreur", "Aucune année scolaire active trouvée.")
                    return
                school_info = repo.get_school_info()
                student_meta = repo.get_student_meta_for_dues(student_id, active_year)
                dues_rows = repo.get_dues_for_export(student_id, active_year)
            if not dues_rows:
                QMessageBox.information(self, "Aucune donnée", "Aucune facture à exporter pour cet élève.")
                return
            student_name = student_meta[0] if student_meta else self.combo_students.currentText()
            class_name = student_meta[1] if student_meta else (self.combo_classes.currentText() or "-")
            year_name = student_meta[2] if student_meta else "-"
            pdf = StudentDuesReportPDF(orientation="L", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            apply_grades_sheet_header(pdf, school_info, "RAPPORT DES FACTURES ET ENGAGEMENTS", "Helvetica")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, pdf.sanitize(f"Eleve: {student_name}"), 0, 1, "L")
            pdf.cell(0, 6, pdf.sanitize(f"Classe: {class_name} | Annee: {year_name}"), 0, 1, "L")
            pdf.cell(0, 6, f"Genere le: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, "L")
            pdf.ln(2)
            headers = ["Description", "Echeance", "Montant", "Remise", "Net", "Statut"]
            col_widths = [110, 35, 30, 30, 30, 35]
            pdf.set_fill_color(30, 41, 59)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            for idx, header in enumerate(headers):
                ln_value = 1 if idx == len(headers) - 1 else 0
                pdf.cell(col_widths[idx], 8, header, 1, ln_value, "C", True)
            total_original = 0.0
            total_discount = 0.0
            total_net = 0.0
            total_paid = 0.0
            total_pending = 0.0
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 9)
            for index, row in enumerate(dues_rows):
                fee_type, fee_desc, due_date, original, discount, net, is_paid = row
                desc = str(fee_desc or fee_type or "-")
                original_val = float(original or 0)
                discount_val = float(discount or 0)
                net_val = float(net or 0)
                status = "Regle" if int(is_paid or 0) == 1 else "En attente"
                total_original += original_val
                total_discount += discount_val
                total_net += net_val
                if int(is_paid or 0) == 1:
                    total_paid += net_val
                else:
                    total_pending += net_val
                if index % 2 == 0:
                    pdf.set_fill_color(245, 247, 250)
                else:
                    pdf.set_fill_color(255, 255, 255)
                pdf.cell(col_widths[0], 7, pdf.sanitize(desc), 1, 0, "L", True)
                pdf.cell(col_widths[1], 7, str(due_date or "-"), 1, 0, "C", True)
                pdf.cell(col_widths[2], 7, f"{original_val:,.0f}", 1, 0, "R", True)
                pdf.cell(col_widths[3], 7, f"{discount_val:,.0f}", 1, 0, "R", True)
                pdf.cell(col_widths[4], 7, f"{net_val:,.0f}", 1, 0, "R", True)
                pdf.cell(col_widths[5], 7, status, 1, 1, "C", True)
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Total Montant: {total_original:,.0f} | Total Remise: {total_discount:,.0f}", 0, 1, "R")
            pdf.cell(
                0,
                6,
                f"Total Net: {total_net:,.0f} | Regle: {total_paid:,.0f}" f" | En attente: {total_pending:,.0f}",
                0,
                1,
                "R",
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            student_slug = self._slugify(student_name)
            class_slug = self._slugify(class_name)
            default_name = f"Factures_Eleve_{student_slug}_{class_slug}_{timestamp}.pdf"
            output_pdf(
                pdf,
                self,
                default_name,
                mode=STUDENT_DUES_REPORT_OUTPUT_MODE,
                dialog_title="Sauvegarder rapport des factures",
                success_save_message="Rapport des factures exporte avec succes.",
                success_print_message="Rapport des factures envoye a l'imprimante.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export du rapport: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentDuesWindow()
    window.show()
    sys.exit(app.exec())
