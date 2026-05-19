import os
import sys
from datetime import datetime

import psycopg2
from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager, log_audit
from pdf_report_style import (
    apply_grades_sheet_header,
    apply_table_body_style,
    apply_table_header_style,
    apply_title_style,
    get_school_info_row,
    set_zebra_row_fill,
)
from print_export_service import get_report_output_mode, output_pdf
from repositories.finance_repo import FinanceRepository
from ui_styles import ThemeManager, apply_shadow_to_widget, get_card_style, get_table_style, get_tabs_style

THEME_AVAILABLE = True
LATE_PAYERS_OUTPUT_MODE = get_report_output_mode("late_payers_mode", "print")
RECEIPT_OUTPUT_MODE = get_report_output_mode("payment_receipt_mode", "print")


def sanitize(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    try:
        return text.encode("latin-1").decode("latin-1")
    except UnicodeEncodeError:
        return text.encode("ascii", "ignore").decode("ascii")


class LatePayersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Retardataires / المتأخرين")
        self.setMinimumSize(800, 500)

        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.setStyleSheet(f"QDialog {{ background-color: {colors.BG_MAIN}; }}")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        title = QLabel("⚠️ Retardataires / المتأخرين")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            title.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_PRIMARY};")
        self.layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Eleve", "Classe", "Factures Non Payées", "Dette"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        if THEME_AVAILABLE:
            self.table.setStyleSheet(get_table_style())
        self.layout.addWidget(self.table)

        btn_print = QPushButton("🖨️ Imprimer la Liste (PDF)")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_print.setStyleSheet(
                f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """
            )
        btn_print.clicked.connect(self.print_list)
        self.layout.addWidget(btn_print)

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return FinanceRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def load_data(self):
        db = DatabaseManager()
        active_year = self.get_active_year_id()
        today = datetime.now().strftime("%Y-%m-%d")

        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            late_payers = repo.list_late_payers(active_year, today)

            self.table.setRowCount(0)
            for payer in late_payers:
                name, cname, invoices, debt = payer

                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(name))
                self.table.setItem(row, 1, QTableWidgetItem(cname))

                inv_item = QTableWidgetItem(invoices)
                if THEME_AVAILABLE:
                    inv_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                self.table.setItem(row, 2, inv_item)

                amount_item = QTableWidgetItem(f"{debt:,.0f} FCFA")
                amount_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                self.table.setItem(row, 3, amount_item)

    def print_list(self):
        pdf = FPDF()
        pdf.add_page()
        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, "LISTE DES RETARDATAIRES", "Arial")
        apply_title_style(pdf, "Arial", 16)
        pdf.set_font("Arial", 'I', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
        pdf.ln(4)

        apply_table_header_style(pdf, "Arial", 10)
        pdf.cell(60, 10, "Eleve", 1, 0, 'C', True)
        pdf.cell(30, 10, "Classe", 1, 0, 'C', True)
        pdf.cell(70, 10, "Factures Non Payees", 1, 0, 'C', True)
        pdf.cell(30, 10, "Dette", 1, 1, 'C', True)

        apply_table_body_style(pdf, "Arial", 10)
        for r in range(self.table.rowCount()):
            name = sanitize(self.table.item(r, 0).text())
            cls = sanitize(self.table.item(r, 1).text())
            months = sanitize(self.table.item(r, 2).text())
            debt = self.table.item(r, 3).text()
            set_zebra_row_fill(pdf, r)

            pdf.cell(60, 8, name, 1, 0, 'L', True)
            pdf.cell(30, 8, cls, 1, 0, 'C', True)

            short_months = months if len(months) <= 30 else months[:27] + "..."
            pdf.cell(70, 8, short_months, 1, 0, 'L', True)

            pdf.cell(30, 8, debt, 1, 1, 'R', True)

        default_name = f"Retardataires_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_pdf(
            pdf,
            self,
            default_name,
            mode=LATE_PAYERS_OUTPUT_MODE,
            dialog_title="Enregistrer PDF",
            success_save_message="Liste PDF générée.",
            success_print_message="Liste envoyée à l'imprimante.",
        )


# --- النافذة الرئيسية للمدفوعات ---
class StudentPaymentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Caisse & Paiements / الصندوق والمدفوعات")
        self.setMinimumSize(1100, 700)

        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)

        self.init_db()
        self.init_ui()
        self.load_classes()

    def _rgba(self, hex_color, alpha=35):
        color = QColor(hex_color)
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"

    def init_db(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # إضافة SAVEPOINT لضمان عدم توقف البرنامج إذا كان الفهرس موجوداً
                cursor.execute("SAVEPOINT sp_idx;")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_student ON Payments(student_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON Payments(transaction_date)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_payments_student_date ON Payments(student_id, transaction_date)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_dues_paid ON StudentDues(is_paid)")
                cursor.execute("RELEASE SAVEPOINT sp_idx;")
            except psycopg2.Error as e:
                cursor.execute("ROLLBACK TO SAVEPOINT sp_idx;")
                AppLogger.warning("FinancePayments", f"Error creating indexes: {e}")

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return FinanceRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        from ui_styles import get_module_caps

        caps = get_module_caps(role, "finance_payments")
        self.btn_validate_payment.setEnabled(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else ThemeManager.get_colors()
        bg_header = colors.BG_HEADER
        header_text = colors.HEADER_TEXT
        sub_text = colors.TEXT_SECONDARY

        header_frame.setStyleSheet(
            f"""
            QFrame {{ background-color: {bg_header}; border-radius: 10px; }}
        """
        )
        header_frame.setFixedHeight(80)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)

        icon_lbl = QLabel("💰")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")

        title_box = QVBoxLayout()
        header_lbl = QLabel("GESTION DE CAISSE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {header_text}; background: transparent;")
        sub_lbl = QLabel("تحصيل الرسوم والفواتير المستحقة")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {sub_text}; background: transparent;")
        title_box.addWidget(header_lbl)
        title_box.addWidget(sub_lbl)

        btn_late = QPushButton("⚠️ Retardataires / المتأخرين")
        btn_late.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_late.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {colors.DANGER}; color: white; font-weight: bold;
                    padding: 10px 20px; border-radius: 6px; border: none;
                }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """
            )
        btn_late.clicked.connect(self.show_late_payers)

        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_box)
        hl.addStretch()
        hl.addWidget(btn_late)

        self.main_layout.addWidget(header_frame)

        # 2. Selection Card
        sel_card = self.create_card()
        slay = QHBoxLayout(sel_card)
        slay.setContentsMargins(20, 20, 20, 20)
        slay.setSpacing(15)

        sel_title = QLabel("Sélection de l'élève / اختيار الطالب")
        if THEME_AVAILABLE:
            sel_title.setStyleSheet(
                f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;"
            )

        self.combo_classes = self.styled_combo()
        self.combo_classes.currentIndexChanged.connect(self.load_students)

        self.combo_students = self.styled_combo()
        self.combo_students.currentIndexChanged.connect(self.load_student_status)

        slay.addWidget(sel_title)
        slay.addWidget(QLabel("Classe:"))
        slay.addWidget(self.combo_classes, 1)
        slay.addWidget(QLabel("Élève:"))
        slay.addWidget(self.combo_students, 2)

        self.main_layout.addWidget(sel_card)

        # 3. Main Tabs (Encaissement + Registre)
        self.main_tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.main_tabs.setStyleSheet(get_tabs_style())

        tab_collect = QWidget()
        tab_collect_layout = QVBoxLayout(tab_collect)
        tab_collect_layout.setContentsMargins(0, 0, 0, 0)
        tab_collect_layout.setSpacing(12)

        # 3.1 Payment Area
        self.dues_frame = self.create_card()
        mlay = QVBoxLayout(self.dues_frame)
        mlay.setContentsMargins(20, 20, 20, 20)

        lbl_month_title = QLabel("Factures à payer / الفواتير والمطالبات المستحقة")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            lbl_month_title.setStyleSheet(
                f"font-weight: bold; color: {colors.TEXT_PRIMARY}; border-bottom: 1px solid {colors.BORDER}; padding-bottom: 5px;"
            )
        mlay.addWidget(lbl_month_title)

        self.dues_grid = QGridLayout()
        self.dues_grid.setSpacing(10)
        mlay.addLayout(self.dues_grid)

        dues_scroll = QScrollArea()
        dues_scroll.setWidgetResizable(True)
        dues_scroll.setFrameShape(QFrame.Shape.NoFrame)
        dues_scroll.setWidget(self.dues_frame)
        tab_collect_layout.addWidget(dues_scroll, 1)

        # 3.2 Calculation & Validation Bar
        action_card = self.create_card()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            action_card.setStyleSheet(
                f"""
                QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 12px; }}
                QLabel {{ color: {colors.HEADER_TEXT}; font-weight: bold; }}
            """
            )
        alay = QHBoxLayout(action_card)
        alay.setContentsMargins(20, 15, 20, 15)
        alay.setSpacing(20)

        self.lbl_total_due = QLabel("Total Sélectionné: 0")
        if THEME_AVAILABLE:
            self.lbl_total_due.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().HEADER_TEXT};")

        self.spin_paid_amount = self.styled_spinbox("Montant Reçu: ")
        self.spin_paid_amount.valueChanged.connect(self.recalc_totals)

        self.lbl_balance = QLabel("Rendu (باقي للصرف): 0")
        if THEME_AVAILABLE:
            self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().WARNING};")

        self.btn_validate_payment = QPushButton("VALIDER L'ENCAISSEMENT")
        self.btn_validate_payment.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate_payment.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.btn_validate_payment.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {colors.SUCCESS}; color: white; font-weight: bold;
                    font-size: 14px; border-radius: 6px; padding: 0 30px; border: none;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """
            )
        self.btn_validate_payment.clicked.connect(self.execute_payment_transaction)

        alay.addWidget(self.lbl_total_due)
        alay.addWidget(self.spin_paid_amount)
        alay.addWidget(self.lbl_balance)
        alay.addStretch()
        alay.addWidget(self.btn_validate_payment)

        tab_collect_layout.addWidget(action_card)

        # 3.3 History Tab
        tab_history = QWidget()
        history_layout = QVBoxLayout(tab_history)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)

        self.table_history = QTableWidget()
        self.style_table(self.table_history)
        self.table_history.setColumnCount(6)
        self.table_history.setHorizontalHeaderLabels(["ID", "Date", "Description", "Montant Total", "Versé", "Reçu"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.table_history)

        self.main_tabs.addTab(tab_collect, "💳 Encaissement")
        self.main_tabs.addTab(tab_history, "📚 Registre Paiements")
        self.main_layout.addWidget(self.main_tabs, 1)

        # Init Data
        self.due_checkboxes = {}
        self.current_total_selected = 0.0

    # --- Helper Styling Methods ---
    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        return frame

    def styled_combo(self):
        combo = QComboBox()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(
                f"""
                QComboBox {{
                    padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px;
                    background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-weight:bold;
                }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """
            )
        combo.setMinimumHeight(40)
        return combo

    def styled_spinbox(self, prefix):
        sb = QDoubleSpinBox()
        sb.setRange(0, 10000000)
        sb.setPrefix(prefix)
        sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            sb.setStyleSheet(
                f"""
                QDoubleSpinBox {{
                    padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px;
                    background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; font-weight: bold;
                }}
            """
            )
        sb.setMinimumHeight(40)
        sb.setFixedWidth(200)
        return sb

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            table.setStyleSheet(
                f"""
                QTableWidget {{
                    background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER};
                    border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item:alternate {{ background-color: {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """
            )

    # --- Logic Methods ---
    def show_late_payers(self):
        dlg = LatePayersDialog(self)
        dlg.exec()

    def load_classes(self):
        self.combo_classes.clear()
        self.combo_classes.addItem("- Choisir Classe -", None)
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            for c in repo.list_classes():
                self.combo_classes.addItem(c[1] or "-", c[0])

    def load_students(self):
        cid = self.combo_classes.currentData()
        self.combo_students.clear()
        if not cid:
            return

        active_year = self.get_active_year_id()
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            for s in repo.list_students_by_class(cid, active_year):
                self.combo_students.addItem(s[1] or "-", s[0])

    def load_student_status(self):
        self.clear_dues_grid()
        self.reset_calcs()
        sid = self.combo_students.currentData()
        if not sid:
            return

        active_year = self.get_active_year_id()
        db = DatabaseManager()

        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            dues = repo.list_dues_for_student(sid, active_year)

        row, col = 0, 0
        for due in dues:
            due_id, desc, net_amt, is_paid, due_date, total_paid = due
            desc_text = desc or f"Facture #{due_id}"

            remaining_amt = net_amt - total_paid

            if remaining_amt <= 0:
                is_paid = 1

            frame = QFrame()
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                bg_color = self._rgba(colors.SUCCESS, 35) if is_paid else self._rgba(colors.WARNING, 35)
                border_color = colors.SUCCESS if is_paid else colors.WARNING

            frame.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 10px;
                }}
            """
            )
            frame.setMinimumHeight(112)
            vb = QVBoxLayout(frame)
            vb.setContentsMargins(10, 10, 10, 10)
            vb.setSpacing(6)

            lbl_desc = QLabel(desc_text)
            lbl_desc.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_desc.setWordWrap(True)

            if total_paid > 0 and not is_paid:
                lbl_amt = QLabel(f"Reste: {remaining_amt:,.0f} FCFA\n(Total: {net_amt:,.0f})")
            else:
                lbl_amt = QLabel(f"{net_amt:,.0f} FCFA")

            lbl_amt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_amt.setWordWrap(True)

            if THEME_AVAILABLE:
                lbl_desc.setStyleSheet(
                    f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; border: none; background: transparent;"
                )
                lbl_amt.setStyleSheet(
                    f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 13px; border: none; background: transparent;"
                )

            chk = QCheckBox("Sélectionner pour Payer")
            chk.setStyleSheet("border: none; background: transparent; font-weight: bold;")

            if is_paid:
                chk.setText("Déjà Payé ✅")
                chk.setChecked(True)
                chk.setEnabled(False)
            else:
                chk.stateChanged.connect(self.update_selection_total)
                self.due_checkboxes[due_id] = (chk, remaining_amt, desc_text)

            vb.addWidget(lbl_desc)
            vb.addWidget(lbl_amt)
            vb.addWidget(chk, 0, Qt.AlignmentFlag.AlignCenter)

            self.dues_grid.addWidget(frame, row, col)

            col += 1
            if col > 2:
                col = 0
                row += 1

        self.load_history(sid)

    def clear_dues_grid(self):
        for i in reversed(range(self.dues_grid.count())):
            self.dues_grid.itemAt(i).widget().setParent(None)
        self.due_checkboxes = {}

    def reset_calcs(self):
        self.spin_paid_amount.setValue(0)
        self.lbl_total_due.setText("Total Sélectionné: 0")
        self.lbl_balance.setText("Rendu: 0")
        self.current_total_selected = 0.0

    def update_selection_total(self):
        total = 0.0
        for _, (chk, amt, _) in self.due_checkboxes.items():
            if chk.isChecked():
                total += amt

        self.current_total_selected = total
        self.lbl_total_due.setText(f"Total Sélectionné: {total:,.0f} FCFA")
        self.spin_paid_amount.setValue(total)
        self.recalc_totals()

    def recalc_totals(self):
        received = self.spin_paid_amount.value()
        to_pay = self.current_total_selected

        balance = received - to_pay

        self.lbl_balance.setText(f"Rendu (باقي للعميل): {max(0, balance):,.0f} FCFA")

        if THEME_AVAILABLE:
            if balance >= 0:
                self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().SUCCESS};")
            else:
                self.lbl_balance.setText(f"Reste à payer (نقص في الدفع): {abs(balance):,.0f} FCFA")
                self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().DANGER};")

    # ─── execute_payment_transaction ─────────────────────────────────────────
    def execute_payment_transaction(self):
        sid = self.combo_students.currentData()
        if not sid or self.current_total_selected <= 0:
            return

        received = self.spin_paid_amount.value()
        if received <= 0:
            QMessageBox.warning(self, "Erreur", "Veuillez saisir un montant valide (أدخل مبلغاً صحيحاً).")
            return

        descriptions = [desc for _due_id, (chk, _amt, desc) in self.due_checkboxes.items() if chk.isChecked()]
        full_description = " | ".join(descriptions)
        if received < self.current_total_selected:
            full_description += " (Paiement Partiel / دفع جزئي)"

        try:
            active_year = self.get_active_year_id()
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                allocations = [
                    {"id": due_id, "amount_due": amt}
                    for due_id, (chk, amt, _) in self.due_checkboxes.items()
                    if chk.isChecked()
                ]
                pid = repo.record_payment(
                    sid,
                    active_year,
                    dt,
                    self.current_total_selected,
                    received,
                    full_description,
                    allocations,
                )
                student_name = self.combo_students.currentText()
                log_audit(
                    conn,
                    getattr(self, "current_user", "system"),
                    "PAYMENT",
                    f"{student_name} - {received:,.0f} FCFA (N°{pid})",
                )
                conn.commit()

            QMessageBox.information(
                self,
                "Succès",
                f"Encaissement validé avec succès (N° {pid}).\n"
                "Le reçu n'est pas imprimé automatiquement."
                " Utilisez le bouton '📄 Reçu' dans le registre si nécessaire.",
            )

            self.load_student_status()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la transaction: {e}")

    def load_history(self, sid):
        self.table_history.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            rows = repo.list_payment_history(sid)

        for row in rows:
            idx = self.table_history.rowCount()
            self.table_history.insertRow(idx)
            for i in range(5):
                self.table_history.setItem(idx, i, QTableWidgetItem(str(row[i])))

            btn = QPushButton("📄 Reçu")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                btn.setStyleSheet(
                    f"background-color: {colors.PRIMARY}; color: white; border-radius: 4px; padding: 2px;"
                )
            btn.clicked.connect(lambda ch, p=row[0]: self.generate_receipt(p))
            self.table_history.setCellWidget(idx, 5, btn)

    def generate_receipt(self, pid):
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            data = repo.get_payment_receipt_data(pid)

        if not data:
            return

        total_due = float(data[4] or 0)
        discount = float(data[5] or 0)
        amount_paid = float(data[6] or 0)

        pdf = FPDF()
        pdf.add_page()
        apply_title_style(pdf, "Arial", 16)
        pdf.cell(0, 10, "RECU DE PAIEMENT", 0, 1, 'C')
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 5, f"No: {data[0]} | Date: {data[1]}", 0, 1, 'C')
        pdf.ln(10)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"ELEVE: {sanitize(data[2])}", 0, 1)
        pdf.cell(0, 8, f"CLASSE: {sanitize(data[3])}", 0, 1)
        pdf.ln(5)

        apply_table_header_style(pdf, "Arial", 11)
        pdf.cell(100, 10, "Description des Factures", 1, 0, 'C', True)
        pdf.cell(40, 10, "Valeur", 1, 1, 'C', True)

        apply_table_body_style(pdf, "Arial", 11)
        set_zebra_row_fill(pdf, 0)
        pdf.multi_cell(100, 10, sanitize(data[8]), 1, 'L', True)

        current_y = pdf.get_y() - 10
        pdf.set_xy(110, current_y)
        pdf.cell(40, 10, f"{total_due:,.0f}", 1, 1, 'R', True)

        if discount > 0:
            set_zebra_row_fill(pdf, 1)
            pdf.cell(100, 10, "Remise (Discount)", 1, 0, 'L', True)
            pdf.cell(40, 10, f"-{discount:,.0f}", 1, 1, 'R', True)

        apply_table_header_style(pdf, "Arial", 12)
        pdf.cell(100, 12, "TOTAL ENCAISSE", 1, 0, 'L', True)
        pdf.cell(40, 12, f"{amount_paid:,.0f} FCFA", 1, 1, 'R', True)

        default_name = f"Recu_{pid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_pdf(
            pdf,
            self,
            default_name,
            mode="print",
            dialog_title="Enregistrer le reçu",
            success_save_message="Reçu PDF généré.",
            success_print_message="Reçu envoyé à l'imprimante.",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentPaymentWindow()
    window.show()
    sys.exit(app.exec())
