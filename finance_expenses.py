import sys
import psycopg2
import os
from datetime import datetime
from database_setup import DatabaseManager
from app_logger import AppLogger
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QDateEdit, 
                             QTabWidget, QDoubleSpinBox, QDialog, QFormLayout, QFrame,
                             QGraphicsDropShadowEffect, QGridLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style, Colors
from repositories.finance_repo import FinanceRepository
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_title_style, apply_grades_sheet_header, apply_table_header_style, apply_table_body_style, set_zebra_row_fill, get_school_info_row

THEME_AVAILABLE = True
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
        
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
            colors = ThemeManager.get_colors()
            self.setStyleSheet(f"""
                QDialog {{ background-color: {colors.BG_MAIN}; }}
                QFrame {{ background-color: {colors.BG_CARD}; border-radius: 10px; border: 1px solid {colors.BORDER}; }}
                QLabel {{ color: {colors.TEXT_PRIMARY}; font-size: 13px; }}
                QDoubleSpinBox {{ 
                    padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; 
                    background-color: {colors.INPUT_BG}; font-weight: bold; color: {colors.TEXT_PRIMARY};
                }}
                QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background-color: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QDialog {{ background-color: {colors.BG_MAIN}; }}
                QFrame {{ background-color: {colors.BG_CARD}; border-radius: 10px; border: 1px solid {colors.BORDER}; }}
                QLabel {{ color: {colors.TEXT_PRIMARY}; font-size: 13px; }}
                QDoubleSpinBox {{ 
                    padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; 
                    background-color: {colors.INPUT_BG}; font-weight: bold; color: {colors.TEXT_PRIMARY};
                }}
            """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Détails du Paiement")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
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
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.lbl_net.setStyleSheet(f"color: {colors.SUCCESS};")
        form_layout.addRow("Net à Payer:", self.lbl_net)

        layout.addWidget(form_frame)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Annuler")
        btn_ok = QPushButton("Confirmer")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_cancel.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY}; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: 1px solid {colors.BORDER}; }}
            QPushButton:hover {{ background-color: {colors.BORDER}; }}
        """)
        btn_ok.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        
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

class ExpensesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion Financière : Dépenses & Salaires / المصاريف والرواتب")
        self.setMinimumSize(1100, 700)
        self.current_report_headers = []
        self.current_report_rows = []
        self.current_report_title = ""
        self.current_report_totals = {}

        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
            """)

        self.init_ui()
        self.load_history()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        header_frame.setStyleSheet(f"""
            QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 10px; }}
        """)
        header_frame.setMaximumHeight(80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15); shadow.setColor(QColor(15, 23, 42, 40)); shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)
        
        icon_lbl = QLabel("💸")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("DÉPENSES & SALAIRES")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إدارة المصاريف العامة ورواتب الموظفين")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; background: transparent;")
        
        title_layout.addWidget(header_lbl)
        title_layout.addWidget(sub_lbl)
        
        hl.addWidget(icon_lbl)
        hl.addSpacing(15)
        hl.addLayout(title_layout)
        hl.addStretch()
        
        self.main_layout.addWidget(header_frame)

        # 2. Tabs
        self.tabs = QTabWidget()
        if THEME_AVAILABLE:
            self.tabs.setStyleSheet(get_tabs_style())
        else:
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{ border: 1px solid {colors.BORDER}; background: {colors.BG_CARD}; border-radius: 12px; margin-top: 15px; }}
                QTabBar::tab {{ background: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 12px 30px; margin-right: 6px; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-family: 'Segoe UI', 'Cairo'; }}
                QTabBar::tab:selected {{ background: {colors.BG_CARD}; color: {colors.PRIMARY}; border-bottom: 2px solid {colors.PRIMARY}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """)
        
        self.setup_expenses_tab()
        self.setup_payroll_tab()
        self.setup_expense_reports_tab()
        
        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_CARD}; border-radius: 12px; border: 1px solid {colors.BORDER}; }}")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20); shadow.setColor(QColor(15, 23, 42, 15)); shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
        return frame

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        le.setStyleSheet(f"""
            QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
            QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """)
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"""
            QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}
            QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
        """)
        combo.setMinimumHeight(38)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())

    # --- Tab 1: General Expenses ---
    def setup_expenses_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Add Expense Card
        add_card = self.create_card()
        v_add = QVBoxLayout(add_card)
        v_add.setContentsMargins(20, 20, 20, 20)
        v_add.setSpacing(15)
        
        # Title
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        card_title = QLabel("Nouvelle Dépense / تسجيل مصروف جديد")
        card_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        v_add.addWidget(card_title)
        
        row1 = QHBoxLayout()
        self.combo_category = self.styled_combo()
        self.combo_category.addItems(["Loyer", "Électricité/Eau", "Fournitures", "Maintenance", "Transport", "Marketing", "Autre"])
        
        self.txt_desc = self.styled_input("Description...")
        self.txt_amount = self.styled_input("Montant (FCFA)")
        
        row1.addWidget(QLabel("Catégorie:"))
        row1.addWidget(self.combo_category)
        row1.addWidget(QLabel("Description:"))
        row1.addWidget(self.txt_desc, 2)
        row1.addWidget(QLabel("Montant:"))
        row1.addWidget(self.txt_amount)
        
        row2 = QHBoxLayout()
        self.txt_beneficiary = self.styled_input("Bénéficiaire (ex: EL MALICK)")
        
        self.date_expense = QDateEdit()
        self.date_expense.setCalendarPopup(True)
        self.date_expense.setDate(QDate.currentDate())
        self.date_expense.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        self.date_expense.setMinimumHeight(38)

        self.btn_save_exp = QPushButton("Enregistrer")
        self.btn_save_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_exp.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        self.btn_save_exp.clicked.connect(self.save_expense)
        
        row2.addWidget(QLabel("Payé à:"))
        row2.addWidget(self.txt_beneficiary)
        row2.addWidget(QLabel("Date:"))
        row2.addWidget(self.date_expense)
        row2.addWidget(self.btn_save_exp)
        
        v_add.addLayout(row1)
        v_add.addLayout(row2)
        layout.addWidget(add_card)
        
        # List
        history_title = QLabel("Historique des Dépenses:")
        history_title.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-weight: bold; margin-top: 10px;")
        layout.addWidget(history_title)

        self.table_expenses = QTableWidget(0, 6)
        self.style_table(self.table_expenses)
        self.table_expenses.setHorizontalHeaderLabels(["ID", "Catégorie", "Description", "Bénéficiaire", "Montant", "Date"])
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
        h_fil.setContentsMargins(20, 20, 20, 20)
        h_fil.setSpacing(15)
        
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        card_title = QLabel("Paiement des Salaires / دفع الرواتب")
        card_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        
        self.date_payroll_month = QDateEdit()
        self.date_payroll_month.setDisplayFormat("MM/yyyy")
        self.date_payroll_month.setDate(QDate.currentDate())
        self.date_payroll_month.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        self.date_payroll_month.setMinimumHeight(38)
        
        btn_load_staff = QPushButton("Charger la Liste / تحميل")
        btn_load_staff.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_load_staff.setStyleSheet(f"""
            QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 10px; border: none; }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_load_staff.clicked.connect(self.load_payroll_list)
        
        h_fil.addWidget(card_title)
        h_fil.addStretch()
        h_fil.addWidget(QLabel("Mois de Paie:"))
        h_fil.addWidget(self.date_payroll_month)
        h_fil.addWidget(btn_load_staff)
        
        layout.addWidget(filter_card)
        
        # Payroll Table
        self.table_payroll = QTableWidget(0, 7)
        self.style_table(self.table_payroll)
        self.table_payroll.setHorizontalHeaderLabels([
            "ID", "Employé", "Contrat", "Base/Heures", "Montant Calc.", "État", "Action"
        ])
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

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        title = QLabel("Rapports Dépenses / تقارير المصروفات")
        title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px;")
        control_layout.addWidget(title)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.combo_exp_report = self.styled_combo()
        self.combo_exp_report.addItem("Synthèse Mensuelle par Catégorie", "monthly_category")
        self.combo_exp_report.addItem("Détail des Dépenses (Période)", "detailed")
        self.combo_exp_report.addItem("Flux de Trésorerie (Dépenses vs Revenus)", "cashflow")

        self.date_exp_report_from = QDateEdit()
        self.date_exp_report_from.setCalendarPopup(True)
        self.date_exp_report_from.setDisplayFormat("dd/MM/yyyy")
        today = QDate.currentDate()
        self.date_exp_report_from.setDate(QDate(today.year(), today.month(), 1))

        self.date_exp_report_to = QDateEdit()
        self.date_exp_report_to.setCalendarPopup(True)
        self.date_exp_report_to.setDisplayFormat("dd/MM/yyyy")
        self.date_exp_report_to.setDate(today)

        date_style = f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}"
        self.date_exp_report_from.setStyleSheet(date_style)
        self.date_exp_report_to.setStyleSheet(date_style)
        self.date_exp_report_from.setMinimumHeight(38)
        self.date_exp_report_to.setMinimumHeight(38)

        self.btn_run_exp_report = QPushButton("Générer")
        self.btn_run_exp_report.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run_exp_report.setStyleSheet(
            f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 10px 14px; border: none; }}"
            f"QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}"
        )

        self.btn_export_exp_report = QPushButton("Exporter PDF")
        self.btn_export_exp_report.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_exp_report.setStyleSheet(
            f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 6px; padding: 10px 14px; border: none; }}"
            f"QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}"
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
        self.lbl_exp_report_summary.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-weight: bold; font-size: 13px;")
        control_layout.addWidget(self.lbl_exp_report_summary)

        layout.addWidget(control_card)

        self.table_exp_reports = QTableWidget(0, 5)
        self.style_table(self.table_exp_reports)
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
                        rows.append([
                            category or "Autre",
                            str(count_rows),
                            f"{amount_value:,.0f} FCFA",
                        ])
                    totals["expenses"] = total_expenses

                elif report_key == "cashflow":
                    title = "Flux de Trésorerie (Dépenses vs Revenus)"
                    headers = ["Mois", "Dépenses (مصاريف)", "Revenus (مداخيل)", "Solde (الصافي)"]

                    exp_by_month = {period: float(amount or 0) for period, amount in repo.get_cashflow_expenses_by_month(from_date, to_date_full)}
                    inc_by_month = {period: float(amount or 0) for period, amount in repo.get_cashflow_revenues_by_month(from_date, to_date_full)}

                    periods = sorted(set(exp_by_month.keys()) | set(inc_by_month.keys()))
                    total_expenses = 0.0
                    total_revenues = 0.0

                    for period in periods:
                        exp_value = exp_by_month.get(period, 0.0)
                        inc_value = inc_by_month.get(period, 0.0)
                        balance = inc_value - exp_value
                        total_expenses += exp_value
                        total_revenues += inc_value
                        rows.append([
                            period,
                            f"{exp_value:,.0f} FCFA",
                            f"{inc_value:,.0f} FCFA",
                            f"{balance:,.0f} FCFA",
                        ])

                    totals["expenses"] = total_expenses
                    totals["revenues"] = total_revenues
                    totals["balance"] = total_revenues - total_expenses

                else:
                    title = "Détail des Dépenses"
                    headers = ["Date", "Catégorie", "Description", "Bénéficiaire", "Montant"]
                    total_expenses = 0.0
                    for expense_date, category, description, paid_to, amount in repo.get_expense_detail_list(from_date, to_date_full):
                        amount_value = float(amount or 0)
                        total_expenses += amount_value
                        display_date = str(expense_date).split(" ")[0] if expense_date else ""
                        rows.append([
                            display_date,
                            category or "",
                            description or "",
                            paid_to or "",
                            f"{amount_value:,.0f} FCFA",
                        ])
                    totals["expenses"] = total_expenses

            return headers, rows, title, totals
        except Exception as e:
            raise e

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
            QMessageBox.critical(self, "Erreur", f"Erreur de rapport: {str(e)}")
            return

        self.current_report_headers = headers
        self.current_report_rows = rows
        self.current_report_title = title
        self.current_report_totals = totals

        self.table_exp_reports.setColumnCount(len(headers))
        self.table_exp_reports.setHorizontalHeaderLabels(headers)
        self.table_exp_reports.setRowCount(0)

        amount_columns = {
            idx for idx, label in enumerate(headers)
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
                            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                            item.setForeground(QColor(colors.SUCCESS if val_num >= 0 else colors.DANGER))
                    except Exception: pass
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
        pdf.cell(0, 8, f"Période: {self.date_exp_report_from.date().toString('dd/MM/yyyy')} - {self.date_exp_report_to.date().toString('dd/MM/yyyy')}", 0, 1, 'C')
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
    def save_expense(self):
        cat = self.combo_category.currentText()
        desc = self.txt_desc.text().strip()
        amt_str = self.txt_amount.text().strip()
        ben = self.txt_beneficiary.text().strip()
        date_v = self.date_expense.date().toString("yyyy-MM-dd")
        
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

            self.txt_desc.clear()
            self.txt_amount.clear()
            self.txt_beneficiary.clear()
            self.load_history()
            self.run_expense_report() # تحديث الإحصائيات إذا كنا في نفس الشهر
            QMessageBox.information(self, "Succès", "Dépense enregistrée avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur BD", str(e))

    def load_history(self):
        self.table_expenses.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                rows = FinanceRepository(conn).list_recent_expenses(limit=50)
            for r in rows:
                idx = self.table_expenses.rowCount()
                self.table_expenses.insertRow(idx)
                for i, val in enumerate(r):
                    if i == 4: # Amount column
                        item = QTableWidgetItem(f"{float(val or 0):,.0f} FCFA")
                        if THEME_AVAILABLE:
                            item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    else:
                        item = QTableWidgetItem(str(val if val is not None else ""))
                    self.table_expenses.setItem(idx, i, item)
        except Exception as e:
            AppLogger.error("FinanceExpenses", f"Error loading expenses history: {e}")

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
                                    t1 = datetime.strptime(cin, "%H:%M")
                                    t2 = datetime.strptime(cout, "%H:%M")
                                    diff = (t2 - t1).total_seconds() / 3600
                                    if diff > 0: total_hours += diff
                                except ValueError:
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
                    if THEME_AVAILABLE:
                        status_item.setForeground(
                            QColor(ThemeManager.get_colors().SUCCESS) if is_paid else QColor(ThemeManager.get_colors().WARNING)
                        )
                    status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_payroll.setItem(idx, 5, status_item)
                    
                    if not is_paid:
                        btn = QPushButton("Payer")
                        btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        if THEME_AVAILABLE:
                            btn.setStyleSheet(f"background-color: {ThemeManager.get_colors().PRIMARY}; color: white; font-weight: bold; border-radius: 4px; border: none;")
                        
                        s_data = {
                            'id': sid, 'name': name, 'role': role, 'contract_type': ctype,
                            'calculated_base': calc_amount, 'hours_worked': hours_worked, 'rate': rate
                        }
                        btn.clicked.connect(lambda ch, d=s_data: self.open_payment_dialog(d))
                        
                        w = QWidget()
                        l = QHBoxLayout(w)
                        l.setContentsMargins(2,2,2,2)
                        l.addWidget(btn)
                        self.table_payroll.setCellWidget(idx, 6, w)
                    else:
                        item_paid = QTableWidgetItem("-")
                        item_paid.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table_payroll.setItem(idx, 6, item_paid)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de chargement: {e}")

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
                    staff_id, month_str, p_data['base'], p_data['hours'],
                    p_data['bonus'], p_data['deduction'], p_data['net'], today
                )
                # 2. Record Expense
                desc = f"Salaire {month_str} - Staff ID {staff_id}"
                repo.insert_expense('Salaire', desc, p_data['net'], today, 'Personnel')
                conn.commit()
            
            # 3. Print PDF
            self.print_payslip(staff_id, month_str, p_data)
            
            QMessageBox.information(self, "Succès", "Paiement effectué avec succès.")
            self.load_payroll_list()
            self.load_history() # تحديث جدول المصاريف
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Le paiement a échoué: {str(e)}")

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
            QMessageBox.critical(self, "Erreur PDF", f"Échec de la génération du PDF: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExpensesWindow()
    window.show()
    sys.exit(app.exec())
