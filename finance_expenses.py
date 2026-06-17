import os
import sys
from datetime import datetime

from fpdf import FPDF
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app_logger import AppLogger
from constants import PAGE_SIZE_DEFAULT
from database_setup import DatabaseManager
from error_codes import DB_QUERY, DB_TRANSACTION, IO_EXPORT, IO_PDF_GEN, log_op_error, new_op_id
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
from ui_components import (
    BaseWindow,
    card_frame,
    compact_icon_btn,
    style_table,
    styled_button,
    styled_combo,
    styled_date_edit,
    styled_input,
)
from ui_styles import Colors, ModuleHeaderWidget, ThemeManager, get_module_caps, get_table_style, get_tabs_style

PAYSLIP_OUTPUT_MODE = get_report_output_mode("payslip_mode", "print")
EXPENSES_REPORT_OUTPUT_MODE = get_report_output_mode("expenses_report_mode", "save")

# --- نافذة تفاصيل دفع الراتب (محسنة) ---


class SalaryPaymentDialog(QDialog):
    def __init__(self, parent=None, staff_data=None, month_str=""):
        super().__init__(parent)
        self.staff_data = staff_data
        self.month_str = month_str
        self.setWindowTitle(f"Paiement Salaire / دفع الراتب - {month_str}")
        self.setMinimumSize(500, 550)

        ThemeManager.apply_theme(self)
        colors = ThemeManager.get_colors()
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: {colors.BG_MAIN}; }}
            QFrame {{ background-color: {colors.BG_CARD}; border-radius: 14px; border: 1px solid {colors.BORDER}; }}
            QLabel {{ color: {colors.TEXT_PRIMARY}; font-size: 13px; }}
            QDoubleSpinBox {{
                padding: 9px 13px; border: 1.5px solid {colors.INPUT_BORDER}; border-radius: 8px;
                background-color: {colors.INPUT_BG}; font-weight: bold; color: {colors.TEXT_PRIMARY};
            }}
            QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}
            QDoubleSpinBox:read-only {{ background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; }}
        """
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("💼 Détails du Paiement")
        title.setStyleSheet(f"font-size:16px; font-weight:700; color:{ThemeManager.get_colors().TEXT_PRIMARY};")
        layout.addWidget(title)

        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        staff_name = self.staff_data.get('name') if self.staff_data else "-"
        staff_role = self.staff_data.get('role') if self.staff_data else "-"
        base_amount = float(self.staff_data.get('calculated_base', 0)) if self.staff_data else 0.0
        hours_worked = float(self.staff_data.get('hours_worked', 0)) if self.staff_data else 0.0

        self.lbl_staff = QLabel(f"{staff_name} ({staff_role})")
        self.lbl_staff.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        form_layout.addRow("Employé:", self.lbl_staff)

        self.spin_base = QDoubleSpinBox()
        self.spin_base.setRange(0, 10000000)
        self.spin_base.setPrefix("FCFA ")
        self.spin_base.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_base.setValue(base_amount)
        self.spin_base.setReadOnly(True)
        form_layout.addRow("Base:", self.spin_base)

        self.spin_hours = QDoubleSpinBox()
        self.spin_hours.setRange(0, 1000)
        self.spin_hours.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.spin_hours.setValue(hours_worked)
        self.spin_hours.setReadOnly(True)
        form_layout.addRow("Heures:", self.spin_hours)

        self.spin_bonus = QDoubleSpinBox()
        self.spin_bonus.setRange(0, 10000000)
        self.spin_bonus.setPrefix("FCFA ")
        self.spin_bonus.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        form_layout.addRow("Bonus (مكافأة):", self.spin_bonus)

        self.spin_deduction = QDoubleSpinBox()
        self.spin_deduction.setRange(0, 10000000)
        self.spin_deduction.setPrefix("FCFA ")
        self.spin_deduction.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        form_layout.addRow("Retenues (خصم):", self.spin_deduction)

        self.lbl_net = QLabel("0 FCFA")
        self.lbl_net.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        colors = ThemeManager.get_colors()
        self.lbl_net.setStyleSheet(f"color: {colors.SUCCESS};")
        form_layout.addRow("Net à Payer:", self.lbl_net)

        layout.addWidget(form_frame)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = styled_button(
            "✕ Annuler",
            bg_color="transparent",
            text_color=colors.TEXT_SECONDARY,
            hover_color=colors.BG_MAIN,
            min_height=42,
        )
        btn_ok = styled_button("✔ Confirmer", bg_color=colors.SUCCESS, hover_color=colors.SUCCESS_HOVER, min_height=42)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self.spin_bonus.valueChanged.connect(self.update_net)
        self.spin_deduction.valueChanged.connect(self.update_net)
        self.update_net()

    def update_net(self):
        base = self.spin_base.value()
        bonus = self.spin_bonus.value()
        deduction = self.spin_deduction.value()
        net = base + bonus - deduction
        self.lbl_net.setText(f"{net:,.0f} FCFA")

    def get_payment_data(self):
        base = self.spin_base.value()
        bonus = self.spin_bonus.value()
        deduction = self.spin_deduction.value()
        net = base + bonus - deduction
        return {
            'base': base,
            'hours': self.spin_hours.value(),
            'bonus': bonus,
            'deduction': deduction,
            'net': net,
        }


# ---------------------------------------------------------------------------
# Expense Dialog
# ---------------------------------------------------------------------------


class ExpenseDialog(QDialog):
    """Popup pour enregistrer une nouvelle dépense générale."""

    CATEGORIES = [
        "Loyer",
        "Électricité/Eau",
        "Fournitures",
        "Maintenance",
        "Transport",
        "Marketing",
        "Autre",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle Dépense / تسجيل مصروف")
        self.setMinimumWidth(500)
        self.setModal(True)
        ThemeManager.apply_theme(self)
        self._build_ui()

    def _build_ui(self):
        colors = ThemeManager.get_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("💸 Nouvelle Dépense")
        lbl_title.setStyleSheet(f"font-size:16px; font-weight:700; color:{colors.TEXT_PRIMARY};")
        layout.addWidget(lbl_title)

        # Row 1: category + description
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        col_cat = QVBoxLayout()
        col_cat.addWidget(QLabel("Catégorie:"))
        self.combo_category = styled_combo()
        self.combo_category.addItems(self.CATEGORIES)
        col_cat.addWidget(self.combo_category)
        row1.addLayout(col_cat)

        col_desc = QVBoxLayout()
        col_desc.addWidget(QLabel("Description:"))
        self.txt_desc = styled_input("Description de la dépense...")
        col_desc.addWidget(self.txt_desc)
        row1.addLayout(col_desc, 2)
        layout.addLayout(row1)

        # Row 2: amount + beneficiary
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        col_amt = QVBoxLayout()
        col_amt.addWidget(QLabel("Montant (FCFA):"))
        self.txt_amount = styled_input("0")
        col_amt.addWidget(self.txt_amount)
        row2.addLayout(col_amt)

        col_ben = QVBoxLayout()
        col_ben.addWidget(QLabel("Payé à / Bénéficiaire:"))
        self.txt_beneficiary = styled_input("Ex: EL MALICK")
        col_ben.addWidget(self.txt_beneficiary)
        row2.addLayout(col_ben, 2)
        layout.addLayout(row2)

        # Date
        layout.addWidget(QLabel("Date de la dépense:"))
        self.date_expense = styled_date_edit(min_height=42)
        self.date_expense.setCalendarPopup(True)
        self.date_expense.setDate(QDate.currentDate())
        layout.addWidget(self.date_expense)

        layout.addSpacing(6)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = styled_button(
            "✕ Annuler",
            bg_color="transparent",
            text_color=colors.TEXT_SECONDARY,
            hover_color=colors.BG_MAIN,
            min_height=42,
        )
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:transparent; border:1.5px solid {colors.BORDER}; color:{colors.TEXT_SECONDARY}; font-weight:700; border-radius:7px; padding:6px 16px; }}"
            f"QPushButton:hover {{ background:{colors.BG_MAIN}; }}"
        )
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = styled_button(
            "✔ Enregistrer", bg_color=colors.SUCCESS, hover_color=colors.SUCCESS_HOVER, min_height=42
        )
        self.btn_save.clicked.connect(self.accept)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

    def get_values(self):
        return {
            "category": self.combo_category.currentText(),
            "description": self.txt_desc.text().strip(),
            "amount_str": self.txt_amount.text().strip(),
            "beneficiary": self.txt_beneficiary.text().strip(),
            "date": self.date_expense.date().toString("yyyy-MM-dd"),
        }


class ExpensesWindow(BaseWindow):
    def __init__(self):
        super().__init__(
            title="Gestion Financière : Dépenses & Salaires / المصاريف والرواتب", min_width=1100, min_height=700
        )
        self.current_report_headers = []
        self.current_report_rows = []
        self.current_report_title = ""
        self.current_report_totals = {}

        self.init_ui()
        self.load_history()

    def apply_rbac(self, role: str) -> None:
        """تطبيق صلاحيات الأزرار بناءً على دور المستخدم — يُستدعى من MainWindow."""
        caps = get_module_caps(role, "expenses_payroll")
        self.btn_add_expense.setEnabled(caps["can_write"])
        self.btn_add_expense.setVisible(caps["can_write"])

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)

        # 1. Header with stat cards
        header = ModuleHeaderWidget(
            icon="💸",
            title="DÉPENSES & SALAIRES",
            subtitle="إدارة المصاريف العامة ورواتب الموظفين",
        )
        self._stat_exp_month = header.add_stat("💸", "Dépenses Ce Mois", "—", "#EF4444")
        self._stat_sal_month = header.add_stat("👥", "Salaires Ce Mois", "—", "#8B5CF6")
        self._stat_nb_trans = header.add_stat("📊", "Nb. Transactions", "—", "#3B82F6")
        self._stat_annual = header.add_stat("📅", "Total Annuel", "—", "#22C55E")
        self.main_layout.addWidget(header)

        # 2. Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tabs_style())
        self.setup_expenses_tab()
        self.setup_payroll_tab()
        self.setup_expense_reports_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        return card_frame()

    def styled_combo(self):
        return styled_combo()

    # --- Tab 1: General Expenses ---
    def setup_expenses_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Toolbar card
        colors = ThemeManager.get_colors()
        toolbar_card = self.create_card()
        t_lay = QHBoxLayout(toolbar_card)
        t_lay.setContentsMargins(12, 8, 12, 8)
        t_lay.setSpacing(8)

        self.btn_add_expense = styled_button(
            "➕ Nouvelle Dépense",
            bg_color=colors.WARNING,
            hover_color="#B45309",
            min_height=32,
        )
        self.btn_add_expense.clicked.connect(self.open_expense_dialog)
        t_lay.addWidget(self.btn_add_expense)
        t_lay.addStretch()
        layout.addWidget(toolbar_card)

        # List
        history_title = QLabel("Historique des Dépenses:")
        history_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-weight: bold; margin-top: 10px;")
        layout.addWidget(history_title)

        self.table_expenses = QTableWidget(0, 6)
        style_table(self.table_expenses)
        self.table_expenses.setHorizontalHeaderLabels(
            ["ID", "Catégorie", "Description", "Bénéficiaire", "Montant", "Date"]
        )
        self.table_expenses.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_expenses)

        self.tabs.addTab(tab, "  💸 Frais Généraux / مصاريف عامة  ")

    # --- Tab 2: Payroll ---
    def setup_payroll_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Filters Card
        filter_card = self.create_card()
        h_fil = QHBoxLayout(filter_card)
        h_fil.setContentsMargins(12, 8, 12, 8)
        h_fil.setSpacing(10)

        colors = ThemeManager.get_colors()
        card_title = QLabel("Paiement des Salaires / دفع الرواتب")
        card_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 13px;")

        self.date_payroll_month = styled_date_edit(date_format="MM/yyyy", min_height=32)
        self.date_payroll_month.setDisplayFormat("MM/yyyy")
        self.date_payroll_month.setDate(QDate.currentDate())

        btn_load_staff = styled_button(
            "Charger la Liste / تحميل",
            bg_color=colors.PRIMARY,
            hover_color=colors.PRIMARY_DARK,
            min_height=32,
        )
        btn_load_staff.clicked.connect(self.load_payroll_list)

        h_fil.addWidget(card_title)
        h_fil.addStretch()
        h_fil.addWidget(QLabel("Mois de Paie:"))
        h_fil.addWidget(self.date_payroll_month)
        h_fil.addWidget(btn_load_staff)

        layout.addWidget(filter_card)

        # Payroll Table
        self.table_payroll = QTableWidget(0, 7)
        style_table(self.table_payroll)
        self.table_payroll.setHorizontalHeaderLabels(
            ["ID", "Employé", "Contrat", "Base/Heures", "Montant Calc.", "État", "Action"]
        )
        self.table_payroll.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_payroll)

        self.tabs.addTab(tab, "  👨‍💼 Salaires / الرواتب  ")

    # --- Tab 3: Expense Reports ---
    def setup_expense_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        control_card = self.create_card()
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(12)

        colors = ThemeManager.get_colors()

        title = QLabel("Rapports Dépenses / تقارير المصروفات")
        title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        control_layout.addWidget(title)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.combo_exp_report = self.styled_combo()
        self.combo_exp_report.addItem("Synthèse Mensuelle par Catégorie", "monthly_category")
        self.combo_exp_report.addItem("Détail des Dépenses (Période)", "detailed")
        self.combo_exp_report.addItem("Flux de Trésorerie (Dépenses vs Revenus)", "cashflow")

        self.date_exp_report_from = styled_date_edit(date_format="dd/MM/yyyy", min_height=42)
        today = QDate.currentDate()
        self.date_exp_report_from.setDate(QDate(today.year(), today.month(), 1))

        self.date_exp_report_to = styled_date_edit(date_format="dd/MM/yyyy", min_height=42)
        self.date_exp_report_to.setDate(today)

        self.btn_run_exp_report = styled_button(
            "Générer",
            bg_color=colors.PRIMARY,
            hover_color=colors.PRIMARY_DARK,
            min_height=42,
        )

        self.btn_export_exp_report = styled_button(
            "Exporter PDF",
            bg_color=colors.SUCCESS,
            hover_color=colors.SUCCESS_HOVER,
            min_height=42,
        )

        filters.addWidget(QLabel("Type:"))
        filters.addWidget(self.combo_exp_report, 2)
        filters.addWidget(QLabel("De:"))
        filters.addWidget(self.date_exp_report_from)
        filters.addWidget(QLabel("À:"))
        filters.addWidget(self.date_exp_report_to)
        filters.addWidget(self.btn_run_exp_report)
        filters.addWidget(self.btn_export_exp_report)
        control_layout.addLayout(filters)

        self.lbl_exp_report_summary = QLabel("Total: 0 FCFA")
        self.lbl_exp_report_summary.setStyleSheet(
            f"color: {colors.TEXT_SECONDARY}; font-weight: bold; font-size: 13px;"
        )
        control_layout.addWidget(self.lbl_exp_report_summary)

        layout.addWidget(control_card)

        self.table_exp_reports = QTableWidget(0, 5)
        style_table(self.table_exp_reports)
        self.table_exp_reports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_exp_reports)

        self.btn_run_exp_report.clicked.connect(self.run_expense_report)
        self.btn_export_exp_report.clicked.connect(self.export_expense_report_pdf)

        self.tabs.addTab(tab, "  📊 Rapports Dépenses / تقارير المصروفات  ")
        self.run_expense_report()

    # --- Report Logic ---
    def fetch_expense_report_data(self, report_key, from_date, to_date):
        headers = []
        rows = []
        title = "Rapport Dépenses"
        totals = {}

        to_date_full = f"{to_date} 23:59:59"

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)

                if report_key == "monthly_category":
                    title = "Synthèse Mensuelle par Catégorie"
                    headers = ["Catégorie", "Nombre", "Montant Total"]
                    total_expenses = 0.0
                    for category, count_rows, amount_total in repo.get_expenses_by_category(from_date, to_date_full):
                        amount_value = float(amount_total or 0)
                        total_expenses += amount_value
                        rows.append(
                            [
                                category or "Autre",
                                str(count_rows),
                                f"{amount_value:,.0f} FCFA",
                            ]
                        )
                    totals["expenses"] = total_expenses

                elif report_key == "cashflow":
                    title = "Flux de Trésorerie (Dépenses vs Revenus)"
                    headers = ["Mois", "Dépenses (مصاريف)", "Revenus (مداخيل)", "Solde (الصافي)"]

                    exp_by_month = {
                        period: float(amount or 0)
                        for period, amount in repo.get_cashflow_expenses_by_month(from_date, to_date_full)
                    }
                    inc_by_month = {
                        period: float(amount or 0)
                        for period, amount in repo.get_cashflow_revenues_by_month(from_date, to_date_full)
                    }

                    periods = sorted(set(exp_by_month.keys()) | set(inc_by_month.keys()))
                    total_expenses = 0.0
                    total_revenues = 0.0

                    for period in periods:
                        exp_value = exp_by_month.get(period, 0.0)
                        inc_value = inc_by_month.get(period, 0.0)
                        balance = inc_value - exp_value
                        total_expenses += exp_value
                        total_revenues += inc_value
                        rows.append(
                            [
                                period,
                                f"{exp_value:,.0f} FCFA",
                                f"{inc_value:,.0f} FCFA",
                                f"{balance:,.0f} FCFA",
                            ]
                        )

                    totals["expenses"] = total_expenses
                    totals["revenues"] = total_revenues
                    totals["balance"] = total_revenues - total_expenses

                else:
                    title = "Détail des Dépenses"
                    headers = ["Date", "Catégorie", "Description", "Bénéficiaire", "Montant"]
                    total_expenses = 0.0
                    for expense_date, category, description, paid_to, amount in repo.get_expense_detail_list(
                        from_date, to_date_full
                    ):
                        amount_value = float(amount or 0)
                        total_expenses += amount_value
                        display_date = str(expense_date).split(" ")[0] if expense_date else ""
                        rows.append(
                            [
                                display_date,
                                category or "",
                                description or "",
                                paid_to or "",
                                f"{amount_value:,.0f} FCFA",
                            ]
                        )
                    totals["expenses"] = total_expenses

            return headers, rows, title, totals
        except Exception:
            # FIX 1: Bare `raise` preserves the original traceback.
            # `raise e` rebinds the exception to this line, erasing the real origin.
            raise

    def run_expense_report(self):
        from_date = self.date_exp_report_from.date().toString("yyyy-MM-dd")
        to_date = self.date_exp_report_to.date().toString("yyyy-MM-dd")

        if from_date > to_date:
            QMessageBox.warning(self, "Attention", "La date de début doit être inférieure ou égale à la date de fin.")
            return

        report_key = self.combo_exp_report.currentData()

        try:
            headers, rows, title, totals = self.fetch_expense_report_data(report_key, from_date, to_date)
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceExpenses", IO_EXPORT, e, _op_id)
            QMessageBox.critical(
                self, f"Erreur [{IO_EXPORT}]", f"Erreur lors de la génération du rapport.\n\nID: {_op_id}"
            )
            return

        self.current_report_headers = headers
        self.current_report_rows = rows
        self.current_report_title = title
        self.current_report_totals = totals

        self.table_exp_reports.setColumnCount(len(headers))
        self.table_exp_reports.setHorizontalHeaderLabels(headers)
        self.table_exp_reports.setRowCount(0)

        amount_columns = {
            idx
            for idx, label in enumerate(headers)
            if any(token in label.lower() for token in ["montant", "dépenses", "revenus", "solde"])
        }

        for row_idx, row_values in enumerate(rows):
            self.table_exp_reports.insertRow(row_idx)
            for col_idx, value in enumerate(row_values):
                item = QTableWidgetItem(str(value))
                if col_idx in amount_columns:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

                    # تلوين خاص للأرقام في التدفق النقدي
                    val_str = str(value).replace(" FCFA", "").replace(",", "")
                    try:
                        val_num = float(val_str)
                        if "solde" in headers[col_idx].lower() or "balance" in headers[col_idx].lower():
                            colors = ThemeManager.get_colors()
                            item.setForeground(QColor(colors.SUCCESS if val_num >= 0 else colors.DANGER))
                    except Exception:
                        pass
                self.table_exp_reports.setItem(row_idx, col_idx, item)

        if report_key == "cashflow":
            summary_text = (
                f"Dépenses: {totals.get('expenses', 0):,.0f} FCFA   |   "
                f"Revenus: {totals.get('revenues', 0):,.0f} FCFA   |   "
                f"Solde Net: {totals.get('balance', 0):,.0f} FCFA"
            )
        else:
            summary_text = f"Total Dépenses: {totals.get('expenses', 0):,.0f} FCFA"

        self.lbl_exp_report_summary.setText(summary_text)

    def export_expense_report_pdf(self):
        if not self.current_report_rows:
            QMessageBox.warning(self, "Attention", "Aucune donnée à exporter.")
            return

        report_key = self.combo_exp_report.currentData() or "report"
        from_date = self.date_exp_report_from.date().toString("yyyyMMdd")
        to_date = self.date_exp_report_to.date().toString("yyyyMMdd")
        default_name = f"Depenses_{report_key}_{from_date}_{to_date}.pdf"

        orientation = 'L' if len(self.current_report_headers) >= 5 else 'P'
        pdf = FPDF(orientation=orientation)
        pdf.add_page()

        school_info = get_school_info_row()

        apply_grades_sheet_header(pdf, school_info, self.current_report_title)
        apply_table_body_style(pdf, "Arial", 10)
        pdf.cell(
            0,
            8,
            f"Période: {self.date_exp_report_from.date().toString('dd/MM/yyyy')} - {self.date_exp_report_to.date().toString('dd/MM/yyyy')}",
            0,
            1,
            'C',
        )
        pdf.ln(3)

        column_count = max(1, len(self.current_report_headers))
        page_width = pdf.w - 20
        col_width = page_width / column_count

        apply_table_header_style(pdf, "Arial", 10)
        for header in self.current_report_headers:
            h_text = str(header).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(col_width, 9, h_text, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 9)
        for row_idx, row_values in enumerate(self.current_report_rows):
            set_zebra_row_fill(pdf, row_idx)
            for value in row_values:
                cell_text = str(value).encode('latin-1', 'ignore').decode('latin-1')
                alignment = 'R' if "FCFA" in cell_text else 'L'
                pdf.cell(col_width, 8, cell_text, 1, 0, alignment, True)
            pdf.ln()

        output_pdf(
            pdf,
            self,
            default_name,
            mode=EXPENSES_REPORT_OUTPUT_MODE,
            dialog_title="Exporter Rapport",
            success_save_message="Rapport exporté avec succès.",
            success_print_message="Rapport envoyé à l'imprimante.",
        )

    # --- Logic: General Expenses ---
    def open_expense_dialog(self):
        dlg = ExpenseDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            self.save_expense(
                vals["category"],
                vals["description"],
                vals["amount_str"],
                vals["beneficiary"],
                vals["date"],
            )

    def save_expense(self, cat, desc, amt_str, ben, date_v):
        if not amt_str or not desc:
            QMessageBox.warning(self, "Erreur", "La description et le montant sont obligatoires.")
            return

        try:
            amt = float(amt_str)
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Montant invalide.")
            return

        if amt <= 0:
            QMessageBox.warning(self, "Erreur", "Le montant doit être supérieur à 0.")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                FinanceRepository(conn).insert_expense(cat, desc, amt, date_v, ben)
                conn.commit()

            self.load_history()
            self.run_expense_report()  # تحديث الإحصائيات إذا كنا في نفس الشهر
            QMessageBox.information(self, "Succès", "Dépense enregistrée avec succès.")
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceExpenses", DB_QUERY, e, _op_id)
            QMessageBox.critical(self, f"Erreur [{DB_QUERY}]", f"Erreur lors du chargement.\n\nID: {_op_id}")

    def load_history(self):
        self.table_expenses.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = FinanceRepository(conn).list_recent_expenses(limit=PAGE_SIZE_DEFAULT)
            for r in rows:
                idx = self.table_expenses.rowCount()
                self.table_expenses.insertRow(idx)
                for i, val in enumerate(r):
                    if i == 4:  # Amount column
                        item = QTableWidgetItem(f"{float(val or 0):,.0f} FCFA")
                        item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    else:
                        item = QTableWidgetItem(str(val if val is not None else ""))
                    self.table_expenses.setItem(idx, i, item)
        except Exception as e:
            AppLogger.error("FinanceExpenses", f"Error loading expenses history: {e}")

        # Refresh stat cards
        self._load_kpi_stats()

    def _load_kpi_stats(self):
        """Met à jour les cartes de statistiques (KPI cards) du mois en cours."""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                today = datetime.now()
                current_month_str = today.strftime("%Y-%m")
                start_date, end_date = self._month_bounds(current_month_str)

                if not start_date:
                    return

                cursor = conn.cursor()

                # 1. Total dépenses du mois
                cursor.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM Expenses WHERE TO_CHAR(CAST(expense_date AS TIMESTAMP), 'YYYY-MM') = %s",
                    (current_month_str,),
                )
                exp_month = float(cursor.fetchone()[0] or 0)
                self._stat_exp_month.set_value(f"{exp_month:,.0f} FCFA")

                # 2. Total salaires du mois
                cursor.execute(
                    "SELECT COALESCE(SUM(net_amount), 0) FROM SalarySlips WHERE month_str = %s",
                    (current_month_str,),
                )
                sal_month = float(cursor.fetchone()[0] or 0)
                self._stat_sal_month.set_value(f"{sal_month:,.0f} FCFA")

                # 3. Nombre de transactions (expenses + salaires)
                cursor.execute(
                    "SELECT COUNT(*) FROM Expenses WHERE TO_CHAR(CAST(expense_date AS TIMESTAMP), 'YYYY-MM') = %s",
                    (current_month_str,),
                )
                exp_count = int(cursor.fetchone()[0] or 0)
                cursor.execute(
                    "SELECT COUNT(*) FROM SalarySlips WHERE month_str = %s",
                    (current_month_str,),
                )
                sal_count = int(cursor.fetchone()[0] or 0)
                self._stat_nb_trans.set_value(str(exp_count + sal_count))

                # 4. Total annuel (dépenses + salaires)
                year_str = today.strftime("%Y")
                year_start = f"{year_str}-01-01"
                # FIX 4: BETWEEN 'YYYY-12-31' only includes up to 00:00:00 on Dec 31.
                # Use an exclusive upper bound (first day of next year) to capture the
                # full day — any transaction time on Dec 31 is included.
                year_end_exclusive = f"{int(year_str) + 1}-01-01"
                cursor.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM Expenses "
                    "WHERE CAST(expense_date AS TIMESTAMP) >= CAST(%s AS TIMESTAMP) "
                    "AND CAST(expense_date AS TIMESTAMP) < CAST(%s AS TIMESTAMP)",
                    (year_start, year_end_exclusive),
                )
                annual_exp = float(cursor.fetchone()[0] or 0)
                cursor.execute(
                    "SELECT COALESCE(SUM(net_amount), 0) FROM SalarySlips WHERE month_str LIKE %s",
                    (f"{year_str}-%",),
                )
                annual_sal = float(cursor.fetchone()[0] or 0)
                self._stat_annual.set_value(f"{annual_exp + annual_sal:,.0f} FCFA")
        except Exception as e:
            AppLogger.error("FinanceExpenses", f"Error loading KPI stats: {e}")

    def _month_bounds(self, month_str):
        try:
            start = datetime.strptime(f"{month_str}-01", "%Y-%m-%d")
        except ValueError:
            return None, None
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    # --- Logic: Payroll ---
    def load_payroll_list(self):
        self.table_payroll.setRowCount(0)
        target_month_str = self.date_payroll_month.date().toString("yyyy-MM")
        start_date, end_date = self._month_bounds(target_month_str)
        if not start_date:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)

                staff_list = repo.list_active_staff_with_salary()

                for staff in staff_list:
                    sid, name, role, ctype, base, rate = staff

                    is_paid = repo.get_salary_slip_exists(sid, target_month_str)

                    calc_desc = ""
                    calc_amount = 0.0
                    hours_worked = 0.0

                    if ctype == 'Monthly':
                        calc_desc = "Salaire Fixe"
                        calc_amount = float(base or 0)
                    else:
                        # Account for varying time formats safely
                        attendances = repo.get_staff_attendance_times(sid, start_date, end_date)

                        total_hours = 0
                        for cin, cout in attendances:
                            if cin and cout:
                                try:
                                    # FIX 2: psycopg2 returns TIME columns as
                                    # datetime.time objects, not strings.
                                    # strptime("%H:%M") also misses "HH:MM:SS" strings.
                                    # Both cases silently zeroed hourly salaries.
                                    if hasattr(cin, 'hour'):
                                        diff = (
                                            (cout.hour * 3600 + cout.minute * 60 + cout.second)
                                            - (cin.hour * 3600 + cin.minute * 60 + cin.second)
                                        ) / 3600
                                    else:
                                        cin_s, cout_s = str(cin), str(cout)
                                        fmt = "%H:%M:%S" if len(cin_s) > 5 else "%H:%M"
                                        t1 = datetime.strptime(cin_s, fmt)
                                        t2 = datetime.strptime(cout_s, fmt)
                                        diff = (t2 - t1).total_seconds() / 3600
                                    if diff > 0:
                                        total_hours += diff
                                except (ValueError, TypeError, AttributeError):
                                    pass

                        hours_worked = total_hours
                        rate_val = float(rate or 0)
                        calc_amount = total_hours * rate_val
                        calc_desc = f"{total_hours:.1f}h x {rate_val:,.0f}"

                    idx = self.table_payroll.rowCount()
                    self.table_payroll.insertRow(idx)

                    self.table_payroll.setItem(idx, 0, QTableWidgetItem(str(sid)))
                    self.table_payroll.setItem(idx, 1, QTableWidgetItem(name or "-"))
                    self.table_payroll.setItem(idx, 2, QTableWidgetItem("Mensuel" if ctype == "Monthly" else "Horaire"))
                    self.table_payroll.setItem(idx, 3, QTableWidgetItem(calc_desc))

                    amt_item = QTableWidgetItem(f"{calc_amount:,.0f} FCFA")
                    amt_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_payroll.setItem(idx, 4, amt_item)

                    status_item = QTableWidgetItem("PAYÉ" if is_paid else "En attente")
                    status_item.setForeground(
                        QColor(ThemeManager.get_colors().SUCCESS)
                        if is_paid
                        else QColor(ThemeManager.get_colors().WARNING)
                    )
                    status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_payroll.setItem(idx, 5, status_item)

                    if not is_paid:
                        btn = QPushButton("Payer")
                        btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        btn.setStyleSheet(
                            f"background-color: {ThemeManager.get_colors().PRIMARY}; color: white; font-weight: bold; border-radius: 4px; border: none;"
                        )

                        s_data = {
                            'id': sid,
                            'name': name,
                            'role': role,
                            'contract_type': ctype,
                            'calculated_base': calc_amount,
                            'hours_worked': hours_worked,
                            'rate': rate,
                        }
                        btn.clicked.connect(lambda ch, d=s_data: self.open_payment_dialog(d))

                        w = QWidget()
                        l = QHBoxLayout(w)  # noqa: E741
                        l.setContentsMargins(2, 2, 2, 2)
                        l.addWidget(btn)
                        self.table_payroll.setCellWidget(idx, 6, w)
                    else:
                        item_paid = QTableWidgetItem("-")
                        item_paid.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table_payroll.setItem(idx, 6, item_paid)
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceExpenses", DB_QUERY, e, _op_id)
            QMessageBox.critical(self, f"Erreur [{DB_QUERY}]", f"Erreur de chargement.\n\nID: {_op_id}")

    def open_payment_dialog(self, staff_data):
        target_month = self.date_payroll_month.date().toString("yyyy-MM")
        dlg = SalaryPaymentDialog(self, staff_data, target_month)
        if dlg.exec():
            payment_data = dlg.get_payment_data()
            self.process_salary_payment(staff_data['id'], target_month, payment_data)

    def process_salary_payment(self, staff_id, month_str, p_data):
        try:
            db = DatabaseManager()
            today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                # 1. Archive Slip
                repo.insert_salary_slip(
                    staff_id,
                    month_str,
                    p_data['base'],
                    p_data['hours'],
                    p_data['bonus'],
                    p_data['deduction'],
                    p_data['net'],
                    today,
                )
                # 2. Record Expense
                desc = f"Salaire {month_str} - Staff ID {staff_id}"
                repo.insert_expense('Salaire', desc, p_data['net'], today, 'Personnel')
                conn.commit()

            # 3. Print PDF
            self.print_payslip(staff_id, month_str, p_data)

            QMessageBox.information(self, "Succès", "Paiement effectué avec succès.")
            self.load_payroll_list()
            self.load_history()  # تحديث جدول المصاريف

        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceExpenses", DB_TRANSACTION, e, _op_id)
            QMessageBox.critical(self, f"Erreur [{DB_TRANSACTION}]", f"Le paiement a échoué.\n\nID: {_op_id}")

    def print_payslip(self, staff_id, month, data):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = FinanceRepository(conn)
                staff = repo.get_staff_name_role(staff_id)
                school = repo.get_school_info()

            pdf = FPDF()
            pdf.add_page()
            apply_grades_sheet_header(pdf, school, "BULLETIN DE PAIE", "Arial")
            apply_title_style(pdf, "Arial", 16)
            pdf.ln(4)

            apply_table_body_style(pdf, "Arial", 12)
            s_name = str(staff[0]).encode('latin-1', 'ignore').decode('latin-1') if staff else "Inconnu"
            s_role = str(staff[1]).encode('latin-1', 'ignore').decode('latin-1') if staff else "Inconnu"

            pdf.cell(0, 8, f"Période: {month}", 0, 1)
            pdf.cell(0, 8, f"Employé: {s_name}", 0, 1)
            pdf.cell(0, 8, f"Fonction: {s_role}", 0, 1)
            pdf.ln(5)

            apply_table_header_style(pdf, "Arial", 10)
            pdf.cell(140, 10, "Description", 1, 0, 'L', True)
            pdf.cell(50, 10, "Montant", 1, 1, 'R', True)

            apply_table_body_style(pdf, "Arial", 10)
            row_idx = 0
            set_zebra_row_fill(pdf, row_idx)
            pdf.cell(140, 8, "Salaire de Base / Honoraire", 1, 0, 'L', True)
            pdf.cell(50, 8, f"{data['base']:,.0f}", 1, 1, 'R', True)
            row_idx += 1

            if data['bonus'] > 0:
                set_zebra_row_fill(pdf, row_idx)
                pdf.cell(140, 8, "Primes & Bonus", 1, 0, 'L', True)
                pdf.cell(50, 8, f"{data['bonus']:,.0f}", 1, 1, 'R', True)
                row_idx += 1

            if data['deduction'] > 0:
                set_zebra_row_fill(pdf, row_idx)
                pdf.cell(140, 8, "Déductions / Avances", 1, 0, 'L', True)
                pdf.cell(50, 8, f"-{data['deduction']:,.0f}", 1, 1, 'R', True)

            apply_table_header_style(pdf, "Arial", 12)
            pdf.cell(140, 12, "NET A PAYER", 1, 0, 'L', True)
            pdf.cell(50, 12, f"{data['net']:,.0f} FCFA", 1, 1, 'R', True)

            pdf.ln(20)
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 10, "Signature de l'Employeur", 0, 1, 'R')

            output_pdf(
                pdf,
                self,
                f"Paie_{staff_id}_{month}.pdf",
                mode=PAYSLIP_OUTPUT_MODE,
                dialog_title="Sauvegarder PDF",
                success_save_message="Bulletin de paie généré.",
                success_print_message="Bulletin de paie envoyé à l'imprimante.",
            )
        except Exception as e:
            _op_id = new_op_id()
            log_op_error("FinanceExpenses", IO_PDF_GEN, e, _op_id)
            QMessageBox.critical(self, f"Erreur [{IO_PDF_GEN}]", f"Échec de la génération du PDF.\n\nID: {_op_id}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExpensesWindow()
    window.show()
    sys.exit(app.exec())
