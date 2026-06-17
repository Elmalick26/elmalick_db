import os
import sys
from datetime import date, datetime

from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from database_setup import DatabaseManager, log_audit
from error_codes import DB_TRANSACTION, log_op_error, new_op_id
from pdf_helpers import ARABIC_SUPPORT, prepare_pdf_text, setup_pdf_arabic_font
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
from ui_components import BaseWindow, create_card, style_table, styled_button, styled_combo, styled_spinbox
from ui_styles import ModuleHeaderWidget, ThemeManager, get_module_caps, get_tabs_style

LATE_PAYERS_OUTPUT_MODE = get_report_output_mode("late_payers_mode", "print")
RECEIPT_OUTPUT_MODE = get_report_output_mode("payment_receipt_mode", "print")


def sanitize(text):
    if not text:
        return ""
    s = str(text)
    return prepare_pdf_text(s) if ARABIC_SUPPORT else s.encode("latin-1", "ignore").decode("latin-1")


class LatePayersDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Retardataires / المتأخرين")
        self.setMinimumSize(800, 500)

        ThemeManager.apply_theme(self)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        colors = ThemeManager.get_colors()
        self.setStyleSheet(f"QDialog {{ background-color: {colors.BG_MAIN}; }}")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        title = QLabel("⚠️ Retardataires / المتأخرين")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_PRIMARY};")
        self.layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Eleve", "Classe", "Factures Non Payées", "Dette"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_table(self.table)
        self.layout.addWidget(self.table)

        btn_print = styled_button(
            "🖨️ Imprimer la Liste (PDF)",
            bg_color=colors.PRIMARY,
            hover_color=colors.PRIMARY_HOVER,
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
        today = datetime.now().strftime("%Y-%m-%d")
        # FIX 1: Merge the two sequential DB connections into one, and add
        # exception handling — previously a DB failure crashed the dialog silently.
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                active_year = repo.get_active_year_id()
                late_payers = repo.list_late_payers(active_year, today)

                self.table.setRowCount(0)
                for payer in late_payers:
                    name, cname, invoices, debt = payer
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(name))
                    self.table.setItem(row, 1, QTableWidgetItem(cname))
                    inv_item = QTableWidgetItem(invoices)
                    inv_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                    self.table.setItem(row, 2, inv_item)
                    amount_item = QTableWidgetItem(f"{debt:,.0f} FCFA")
                    amount_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                    self.table.setItem(row, 3, amount_item)
        except Exception as e:
            AppLogger.error("LatePayersDialog", f"Error loading late payers: {e}")

    def print_list(self):
        pdf = FPDF()
        setup_pdf_arabic_font(pdf)
        font = "ArabicFont" if ARABIC_SUPPORT else "Arial"
        pdf.add_page()
        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, "LISTE DES RETARDATAIRES", font)
        apply_title_style(pdf, font, 16)
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
class StudentPaymentWindow(BaseWindow):
    def __init__(self):
        super().__init__(title="Caisse & Paiements / الصندوق والمدفوعات", min_width=1100, min_height=700)

        self.init_ui()
        self.load_classes()
        self._load_kpi_stats()

    def _rgba(self, hex_color, alpha=35):
        color = QColor(hex_color)
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"

    def get_active_year_id(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                return FinanceRepository(conn).get_active_year_id()
        except Exception:
            return -1

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "finance_payments")
        if hasattr(self, "btn_validate_payment"):
            self.btn_validate_payment.setEnabled(caps["can_write"])
            self.btn_validate_payment.setVisible(caps["can_write"])

    def init_ui(self):
        # 1. Header
        header = ModuleHeaderWidget(
            icon="💰",
            title="GESTION DE CAISSE",
            subtitle="تحصيل الرسوم والفواتير المستحقة",
        )
        colors = ThemeManager.get_colors()
        btn_late = styled_button(
            "⚠️ Retardataires / المتأخرين",
            bg_color=colors.DANGER,
            hover_color=colors.DANGER_HOVER,
        )
        btn_late.clicked.connect(self.show_late_payers)
        header.layout().addWidget(btn_late)
        header.layout().addSpacing(10)
        self.main_layout.addWidget(header)
        self._stat_total = header.add_stat("💳", "Paiements Total", "—", "#3B82F6")
        self._stat_month = header.add_stat("📅", "Ce Mois", "—", "#22C55E")
        self._stat_late = header.add_stat("⚠️", "En Retard", "—", "#EF4444")
        self._stat_amount = header.add_stat("💰", "Montant Annuel", "—", "#8B5CF6")

        # 2. KPI Cards

        # 2. Selection Card
        sel_card, slay = create_card(layout_class=QHBoxLayout)
        slay.setContentsMargins(20, 20, 20, 20)
        slay.setSpacing(15)

        sel_title = QLabel("Sélection de l'élève / اختيار الطالب")
        sel_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")

        self.combo_classes = styled_combo()
        self.combo_classes.currentIndexChanged.connect(self.load_students)

        self.combo_students = styled_combo()
        self.combo_students.currentIndexChanged.connect(self.load_student_status)

        slay.addWidget(sel_title)
        slay.addWidget(QLabel("Classe:"))
        slay.addWidget(self.combo_classes, 1)
        slay.addWidget(QLabel("Élève:"))
        slay.addWidget(self.combo_students, 2)

        self.main_layout.addWidget(sel_card)

        # 3. Main Tabs (Encaissement + Registre)
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(get_tabs_style())

        tab_collect = QWidget()
        tab_collect_layout = QVBoxLayout(tab_collect)
        tab_collect_layout.setContentsMargins(0, 0, 0, 0)
        tab_collect_layout.setSpacing(12)

        # 3.1 Payment Area
        self.dues_frame, mlay = create_card()
        mlay.setContentsMargins(20, 20, 20, 20)

        lbl_month_title = QLabel("Factures à payer / الفواتير والمطالبات المستحقة")
        colors = ThemeManager.get_colors()
        lbl_month_title.setStyleSheet(
            f"font-weight:700; font-size:12px; color:{colors.PRIMARY};"
            f"padding:6px 12px; border-radius:8px; background:{colors.PRIMARY_LIGHT};"
            f"border-left:3px solid {colors.PRIMARY}; margin-top:4px;"
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
        action_card, alay = create_card(layout_class=QHBoxLayout)
        colors = ThemeManager.get_colors()
        action_card.setStyleSheet(
            f"""
            QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 16px; }}
            QLabel {{ color: {colors.HEADER_TEXT}; font-weight: bold; }}
        """
        )
        alay.setContentsMargins(20, 15, 20, 15)
        alay.setSpacing(20)

        self.lbl_total_due = QLabel("Total Sélectionné: 0")
        self.lbl_total_due.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().HEADER_TEXT};")

        self.spin_paid_amount = styled_spinbox("Montant Reçu: ")
        self.spin_paid_amount.valueChanged.connect(self.recalc_totals)

        self.lbl_balance = QLabel("Rendu (باقي للصرف): 0")
        self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().WARNING};")

        self.btn_validate_payment = styled_button(
            "VALIDER L'ENCAISSEMENT",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=46,
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
        style_table(self.table_history)
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

    # --- Logic Methods ---
    def _load_kpi_stats(self):
        try:
            today = date.today()
            month_start = today.replace(day=1).isoformat()
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                year_id = FinanceRepository(conn).get_active_year_id()
                cursor.execute("SELECT COUNT(*) FROM Payments WHERE year_id = %s", (year_id,))
                total = cursor.fetchone()[0] or 0
                cursor.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM Payments WHERE year_id = %s", (year_id,))
                amount = cursor.fetchone()[0] or 0
                cursor.execute(
                    "SELECT COALESCE(SUM(amount_paid), 0) FROM Payments "
                    "WHERE year_id = %s AND transaction_date >= %s",
                    (year_id, month_start),
                )
                month_amount = cursor.fetchone()[0] or 0
                cursor.execute(
                    "SELECT COUNT(DISTINCT student_id) FROM StudentDues " "WHERE is_paid = 0 AND year_id = %s",
                    (year_id,),
                )
                late = cursor.fetchone()[0] or 0
            self._stat_total.set_value(str(total))
            self._stat_month.set_value(f"{month_amount:,.0f}")
            self._stat_late.set_value(str(late))
            self._stat_amount.set_value(f"{amount:,.0f}")
        except Exception as e:
            AppLogger.warning("FinancePayments", f"KPI load error: {e}")

    def show_late_payers(self):
        dlg = LatePayersDialog(self)
        dlg.exec()

    def load_classes(self):
        self.combo_classes.clear()
        self.combo_classes.addItem("- Choisir Classe -", None)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                for c in repo.list_classes():
                    self.combo_classes.addItem(c[1] or "-", c[0])
        except Exception as e:
            AppLogger.error("FinancePayments", f"Error loading classes: {e}")

    def load_students(self):
        cid = self.combo_classes.currentData()
        self.combo_students.clear()
        if not cid:
            return

        # FIX 2: Fetch active_year inside the same connection instead of
        # calling self.get_active_year_id() which opens a second DB connection.
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            active_year = repo.get_active_year_id()
            for s in repo.list_students_by_class(cid, active_year):
                self.combo_students.addItem(s[1] or "-", s[0])

    def load_student_status(self):
        self.clear_dues_grid()
        self.reset_calcs()
        sid = self.combo_students.currentData()
        if not sid:
            return

        # FIX 2: Same pattern — merge into one connection.
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = FinanceRepository(conn)
            active_year = repo.get_active_year_id()
            dues = repo.list_dues_for_student(sid, active_year)

        row, col = 0, 0
        for due in dues:
            due_id, desc, net_amt, is_paid, due_date, total_paid = due
            desc_text = desc or f"Facture #{due_id}"

            remaining_amt = net_amt - total_paid

            if remaining_amt <= 0:
                is_paid = 1

            frame = QFrame()
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
        self.lbl_balance.setText("Rendu (باقي للعميل): 0 FCFA")
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
            # FIX 2: Same pattern — active_year fetched inside the transaction.
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                active_year = repo.get_active_year_id()
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
            _op_id = new_op_id()
            log_op_error("FinancePayments", DB_TRANSACTION, e, _op_id)
            QMessageBox.critical(self, f"Erreur [{DB_TRANSACTION}]", f"Erreur lors de la transaction.\n\nID: {_op_id}")

    def load_history(self, sid):
        colors = ThemeManager.get_colors()
        self.table_history.setRowCount(0)
        rows = []
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                rows = repo.list_payment_history(sid)
        except Exception as e:
            AppLogger.error("FinancePayments", f"Error loading payment history: {e}")

        for row in rows:
            idx = self.table_history.rowCount()
            self.table_history.insertRow(idx)
            for i in range(5):
                self.table_history.setItem(idx, i, QTableWidgetItem(str(row[i])))

            btn = styled_button(
                "📄 Reçu",
                bg_color=colors.PRIMARY,
                hover_color=colors.PRIMARY_HOVER,
                min_height=28,
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
            # FIX 4: Use the configured constant instead of hardcoded "print".
            mode=RECEIPT_OUTPUT_MODE,
            dialog_title="Enregistrer le reçu",
            success_save_message="Reçu PDF généré.",
            success_print_message="Reçu envoyé à l'imprimante.",
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentPaymentWindow()
    window.show()
    sys.exit(app.exec())
