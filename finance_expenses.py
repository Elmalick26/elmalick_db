import sys
import sqlite3
import os
import subprocess
from datetime import datetime
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QDateEdit, 
                             QTabWidget, QDoubleSpinBox, QDialog, QFormLayout, QFrame,
                             QGraphicsDropShadowEffect, QGridLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from fpdf import FPDF

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True

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
                    background-color: {colors.BG_CARD}; font-weight: bold; color: {colors.TEXT_PRIMARY};
                }}
            """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Details du Paiement")
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
        form_layout.addRow("Employe:", self.lbl_staff)

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
        form_layout.addRow("Bonus:", self.spin_bonus)

        self.spin_deduction = QDoubleSpinBox()
        self.spin_deduction.setRange(0, 10000000)
        self.spin_deduction.setPrefix("FCFA ")
        self.spin_deduction.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        form_layout.addRow("Retenues:", self.spin_deduction)

        self.lbl_net = QLabel("0 FCFA")
        self.lbl_net.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        form_layout.addRow("Net:", self.lbl_net)

        layout.addWidget(form_frame)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Annuler")
        btn_ok = QPushButton("Confirmer")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_ok.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px; border: none; }}
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
        self.setWindowTitle("Gestion Financiere : Depenses & Salaires / المصاريف والرواتب")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)

        self.init_ui()
        self.load_history()

    # init_db removed - managed by database_setup.py

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else ThemeManager.get_colors()
        bg_header = colors.BG_HEADER
        header_text = colors.HEADER_TEXT
        sub_text = colors.TEXT_SECONDARY

        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_header};
                border-radius: 10px;
            }}
        """)
        header_frame.setMaximumHeight(80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)
        
        icon_lbl = QLabel("💸")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("DÉPENSES & SALAIRES")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {header_text}; background: transparent;")
        
        sub_lbl = QLabel("إدارة المصاريف العامة ورواتب الموظفين")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {sub_text}; background: transparent;")
        
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
            colors = ThemeManager.get_colors()
            self.tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {colors.BORDER};
                    background: {colors.BG_CARD};
                    border-radius: 12px;
                    margin-top: 15px;
                }}
                QTabBar::tab {{
                    background: {colors.BG_MAIN};
                    color: {colors.TEXT_SECONDARY};
                    padding: 12px 30px;
                    margin-right: 6px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: bold;
                    font-family: 'Segoe UI', 'Cairo';
                }}
                QTabBar::tab:selected {{
                    background: {colors.BG_CARD};
                    color: {colors.PRIMARY};
                    border-bottom: 2px solid {colors.PRIMARY};
                }}
                QTabBar::tab:hover {{
                    background: {colors.BORDER};
                }}
            """)
        
        self.setup_expenses_tab()
        self.setup_payroll_tab()
        
        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        return frame

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            le.setStyleSheet(f"""
                QLineEdit {{ 
                    padding: 8px 12px; 
                    border: 1px solid {colors.BORDER}; 
                    border-radius: 6px; 
                    background: {colors.INPUT_BG}; 
                    color: {colors.TEXT_PRIMARY}; 
                }}
                QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        le.setMinimumHeight(38)
        return le

    def styled_combo(self):
        combo = QComboBox()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            combo.setStyleSheet(f"""
                QComboBox {{
                    padding: 8px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                }}
                QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        combo.setMinimumHeight(38)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {colors.BG_CARD};
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    gridline-color: {colors.BORDER};
                    font-size: 13px;
                    color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item {{
                    padding: 6px;
                    border-bottom: 1px solid {colors.BG_MAIN};
                    color: {colors.TEXT_PRIMARY};
                }}
                QTableWidget::item:alternate {{
                    background-color: {colors.BG_MAIN};
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.PRIMARY};
                    color: white;
                }}
                QHeaderView::section {{
                    background-color: {colors.BG_HEADER};
                    color: {colors.HEADER_TEXT};
                    padding: 10px;
                    border: none;
                    font-weight: bold;
                }}
            """)

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
        card_title = QLabel("Nouvelle Dépense / تسجيل مصروف")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        v_add.addWidget(card_title)
        
        row1 = QHBoxLayout()
        self.combo_category = self.styled_combo()
        self.combo_category.addItems(["Loyer", "Electricité/Eau", "Fournitures", "Maintenance", "Transport", "Marketing", "Autre"])
        
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
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.date_expense.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        else:
            colors = Colors()
            self.date_expense.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        self.date_expense.setMinimumHeight(38)

        self.btn_save_exp = QPushButton("Enregistrer")
        self.btn_save_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
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
        layout.addWidget(QLabel("Historique des Dépenses:"))
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
        
        card_title = QLabel("Paiement des Salaires / دفع الرواتب")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        
        self.date_payroll_month = QDateEdit()
        self.date_payroll_month.setDisplayFormat("MM/yyyy")
        self.date_payroll_month.setDate(QDate.currentDate())
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.date_payroll_month.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        else:
            colors = Colors()
            self.date_payroll_month.setStyleSheet(f"QDateEdit {{ padding: 8px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        self.date_payroll_month.setMinimumHeight(38)
        
        btn_load_staff = QPushButton("Charger la Liste / تحميل")
        btn_load_staff.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
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

    # --- Logic: General Expenses ---
    def save_expense(self):
        cat = self.combo_category.currentText()
        desc = self.txt_desc.text()
        amt = self.txt_amount.text()
        ben = self.txt_beneficiary.text()
        date_v = self.date_expense.date().toString("yyyy-MM-dd")
        
        if not amt or not desc: return
        
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("INSERT INTO Expenses (category, description, amount, expense_date, paid_to) VALUES (?,?,?,?,?)",
                            (cat, desc, float(amt), date_v, ben))
                conn.commit()
                
            self.txt_desc.clear(); self.txt_amount.clear()
            self.load_history()
            QMessageBox.information(self, "Succès", "Dépense enregistrée.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def load_history(self):
        self.table_expenses.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, category, description, paid_to, amount, expense_date FROM Expenses ORDER BY expense_date DESC LIMIT 50")
            for r in cur.fetchall():
                idx = self.table_expenses.rowCount()
                self.table_expenses.insertRow(idx)
                for i, val in enumerate(r):
                    item = QTableWidgetItem(str(val))
                    if i == 4: # Amount column
                        item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.table_expenses.setItem(idx, i, item)

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
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT id, first_name || ' ' || last_name, role, contract_type, salary_base, hourly_rate FROM Staff WHERE status='Actif'")
            staff_list = cur.fetchall()
            
            for staff in staff_list:
                sid, name, role, ctype, base, rate = staff
                
                # Check paid
                cur.execute("SELECT id FROM SalarySlips WHERE staff_id=? AND month_str=?", (sid, target_month_str))
                is_paid = cur.fetchone()
                
                calc_desc = ""
                calc_amount = 0.0
                hours_worked = 0.0
                
                if ctype == 'Monthly':
                    calc_desc = "Salaire Fixe"
                    calc_amount = base
                else:
                    # Calculate hours
                    cur.execute("""
                        SELECT check_in_time, check_out_time 
                        FROM StaffAttendance 
                        WHERE staff_id=? AND attendance_date >= ? AND attendance_date < ?
                    """, (sid, start_date, end_date))
                    attendances = cur.fetchall()
                    
                    total_hours = 0
                    for cin, cout in attendances:
                        if cin and cout:
                            try:
                                t1 = datetime.strptime(cin, "%H:%M")
                                t2 = datetime.strptime(cout, "%H:%M")
                                diff = (t2 - t1).total_seconds() / 3600
                                if diff > 0: total_hours += diff
                            except: pass
                    
                    hours_worked = total_hours
                    calc_amount = total_hours * rate
                    calc_desc = f"{total_hours:.1f}h x {rate}"

                idx = self.table_payroll.rowCount()
                self.table_payroll.insertRow(idx)
                
                self.table_payroll.setItem(idx, 0, QTableWidgetItem(str(sid)))
                self.table_payroll.setItem(idx, 1, QTableWidgetItem(name))
                self.table_payroll.setItem(idx, 2, QTableWidgetItem("Mensuel" if ctype == "Monthly" else "Horaire"))
                self.table_payroll.setItem(idx, 3, QTableWidgetItem(calc_desc))
                self.table_payroll.setItem(idx, 4, QTableWidgetItem(f"{calc_amount:,.0f}"))
                
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
                        'id': sid, 'name': name, 'role': role, 'contract_type': ctype,
                        'calculated_base': calc_amount, 'hours_worked': hours_worked, 'rate': rate
                    }
                    btn.clicked.connect(lambda ch, d=s_data: self.open_payment_dialog(d))
                    
                    # Widget wrapper for centering
                    w = QWidget()
                    l = QHBoxLayout(w)
                    l.setContentsMargins(2,2,2,2)
                    l.addWidget(btn)
                    self.table_payroll.setCellWidget(idx, 6, w)
                else:
                    self.table_payroll.setItem(idx, 6, QTableWidgetItem("-"))

    def open_payment_dialog(self, staff_data):
        target_month = self.date_payroll_month.date().toString("yyyy-MM")
        dlg = SalaryPaymentDialog(self, staff_data, target_month)
        if dlg.exec():
            payment_data = dlg.get_payment_data()
            self.process_salary_payment(staff_data['id'], target_month, payment_data)

    def process_salary_payment(self, staff_id, month_str, p_data):
        db = DatabaseManager()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            with db.get_connection() as conn:
                # 1. Archive Slip
                conn.execute("""
                    INSERT INTO SalarySlips (staff_id, month_str, basic_amount, hours_worked, bonuses, deductions, net_amount, payment_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (staff_id, month_str, p_data['base'], p_data['hours'], p_data['bonus'], p_data['deduction'], p_data['net'], today))
                
                # 2. Record Expense
                desc = f"Salaire {month_str} - Staff ID {staff_id}"
                conn.execute("""
                    INSERT INTO Expenses (category, description, amount, expense_date, paid_to)
                    VALUES ('Salaire', ?, ?, ?, 'Personnel')
                """, (desc, p_data['net'], today))
                
                conn.commit()
            
            # 3. Print PDF
            self.print_payslip(staff_id, month_str, p_data)
            
            QMessageBox.information(self, "Succès", "Paiement effectué.")
            self.load_payroll_list()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def print_payslip(self, staff_id, month, data):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT first_name || ' ' || last_name, role FROM Staff WHERE id=?", (staff_id,))
            staff = cur.fetchone()
            try:
                cur.execute("SELECT * FROM SchoolInfo LIMIT 1")
                school = cur.fetchone()
            except: school = None
        
        pdf = FPDF()
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 16)
        school_name = str(school[4]).encode('latin-1', 'ignore').decode('latin-1') if school else "ECOLE"
        pdf.cell(0, 10, school_name, 0, 1, 'C')
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "BULLETIN DE PAIE", 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font("Arial", '', 12)
        s_name = str(staff[0]).encode('latin-1', 'ignore').decode('latin-1')
        pdf.cell(0, 8, f"Periode: {month}", 0, 1)
        pdf.cell(0, 8, f"Employe: {s_name}", 0, 1)
        pdf.cell(0, 8, f"Fonction: {staff[1]}", 0, 1)
        pdf.ln(5)
        
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(140, 10, "Description", 1, 0, 'L', True)
        pdf.cell(50, 10, "Montant", 1, 1, 'R', True)
        
        pdf.cell(140, 8, "Salaire de Base / Honoraire", 1)
        pdf.cell(50, 8, f"{data['base']:,.0f}", 1, 1, 'R')
        
        if data['bonus'] > 0:
            pdf.cell(140, 8, "Primes & Bonus", 1)
            pdf.cell(50, 8, f"{data['bonus']:,.0f}", 1, 1, 'R')
            
        if data['deduction'] > 0:
            pdf.cell(140, 8, "Deductions / Avances", 1)
            pdf.cell(50, 8, f"-{data['deduction']:,.0f}", 1, 1, 'R')
            
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(140, 12, "NET A PAYER", 1)
        pdf.cell(50, 12, f"{data['net']:,.0f} FCFA", 1, 1, 'R')
        
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Signature de l'Employeur", 0, 1, 'R')
        
        filename = f"Paie_{staff_id}_{month}.pdf"
        pdf.output(filename)
        if os.name == 'nt': os.startfile(filename)
        else: subprocess.call(('xdg-open', filename))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExpensesWindow()
    window.show()
    sys.exit(app.exec())