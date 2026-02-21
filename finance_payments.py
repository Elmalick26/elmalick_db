import sys
import sqlite3
import os
import subprocess
from datetime import datetime
from database_setup import DatabaseManager
from fpdf import FPDF
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QCheckBox, 
                             QScrollArea, QFrame, QGridLayout, QDoubleSpinBox, QDialog,
                             QGraphicsDropShadowEffect, QFileDialog)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from ui_styles import ThemeManager, get_card_style, apply_shadow_to_widget, get_table_style

THEME_AVAILABLE = True


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
        self.table.setHorizontalHeaderLabels(["Eleve", "Classe", "Mois Non Payes", "Dette"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        if THEME_AVAILABLE:
            self.table.setStyleSheet(get_table_style())
        self.layout.addWidget(self.table)

        btn_print = QPushButton("🖨️ Imprimer la Liste (PDF)")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_print.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_print.clicked.connect(self.print_list)
        self.layout.addWidget(btn_print)

    def load_data(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            today = datetime.now()
            current_month = today.month
            current_day = today.day

            # Academic months logic (Oct -> June)
            academic_order = [10, 11, 12, 1, 2, 3, 4, 5, 6]
            due_months = []

            for m in academic_order:
                if m > 9:  # Oct-Dec
                    if current_month < 9 or (current_month > 9 and current_month > m) or (current_month == m and current_day >= 10):
                        due_months.append(m)
                else:  # Jan-Jun
                    if current_month >= m and current_day >= 10:
                        due_months.append(m)

            cursor.execute("""
                SELECT S.id, S.first_name_fr || ' ' || S.last_name_fr, C.class_name_fr, S.class_id
                FROM Students S JOIN Classes C ON S.class_id = C.id
                WHERE S.status='Active'
            """)
            students = cursor.fetchall()

            self.table.setRowCount(0)
            for std in students:
                sid, name, cname, cid = std

                cursor.execute("SELECT month_index FROM MonthlyPaymentsStatus WHERE student_id=?", (sid,))
                paid = [r[0] for r in cursor.fetchall()]

                cursor.execute("SELECT month_index, amount FROM MonthlyFeeSchedule WHERE class_id=?", (cid,))
                schedule = {r[0]: r[1] for r in cursor.fetchall()}

                late_months = []
                total_debt = 0

                for dm in due_months:
                    if dm not in paid:
                        m_name = datetime(2000, dm, 1).strftime('%b')
                        late_months.append(m_name)
                        total_debt += schedule.get(dm, 0)

                if late_months:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(name))
                    self.table.setItem(row, 1, QTableWidgetItem(cname))

                    months_item = QTableWidgetItem(", ".join(late_months))
                    if THEME_AVAILABLE:
                        months_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                    self.table.setItem(row, 2, months_item)

                    amount_item = QTableWidgetItem(f"{total_debt:,.0f} FCFA")
                    amount_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                    self.table.setItem(row, 3, amount_item)

        conn.close()

    def print_list(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "LISTE DES RETARDATAIRES", 0, 1, 'C')
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(60, 10, "Eleve", 1, 0, 'C', True)
        pdf.cell(30, 10, "Classe", 1, 0, 'C', True)
        pdf.cell(70, 10, "Mois Non Payes", 1, 0, 'C', True)
        pdf.cell(30, 10, "Dette", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 10)
        for r in range(self.table.rowCount()):
            name = sanitize(self.table.item(r, 0).text())
            cls = sanitize(self.table.item(r, 1).text())
            months = sanitize(self.table.item(r, 2).text())
            debt = self.table.item(r, 3).text()
            
            pdf.cell(60, 8, name, 1)
            pdf.cell(30, 8, cls, 1)
            pdf.cell(70, 8, months, 1)
            pdf.cell(30, 8, debt, 1, 1, 'R')
            
        default_name = f"Retardataires_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer PDF", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return

        pdf.output(file_path)
        if os.name == 'nt': os.startfile(file_path)
        else: subprocess.call(('xdg-open', file_path))


# --- النافذة الرئيسية للمدفوعات ---
class StudentPaymentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Caisse & Paiements / الصندوق والمدفوعات")
        self.setMinimumSize(1100, 700)
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        
        self.init_db()  # Now handled centrally, but we might want to ensure indexes
        self.init_ui()
        self.load_classes()

    def _rgba(self, hex_color, alpha=35):
        color = QColor(hex_color)
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"

    def init_db(self):
        # Database structure is now handled by DatabaseManager in database_setup.py
        # We can just ensure indexes here if they are specific to this module
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # إنشاء indexes للأداء
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_student ON Payments(student_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON Payments(transaction_date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_student_date ON Payments(student_id, transaction_date)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_status_student ON MonthlyPaymentsStatus(student_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_status_student_month ON MonthlyPaymentsStatus(student_id, month_index)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_status_payment ON MonthlyPaymentsStatus(payment_id)")
            except sqlite3.Error as e:
                print(f"Error creating indexes: {e}")


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

        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_header};
                border-radius: 10px;
            }}
        """)
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
        sub_lbl = QLabel("تحصيل الرسوم والأقساط")
        sub_lbl.setFont(QFont("Cairo", 11))
        sub_lbl.setStyleSheet(f"color: {sub_text}; background: transparent;")
        title_box.addWidget(header_lbl)
        title_box.addWidget(sub_lbl)
        
        btn_late = QPushButton("⚠️ Retardataires / المتأخرين")
        btn_late.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_late.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.DANGER}; color: white; font-weight: bold; 
                    padding: 10px 20px; border-radius: 6px; border: none;
                }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
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
        
        # Add Title inside card
        sel_title = QLabel("Sélection de l'élève / اختيار الطالب")
        if THEME_AVAILABLE:
            sel_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px;")
        
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

        # 3. Payment Area (Two Cards Horizontal)
        pay_layout = QHBoxLayout()
        
        # 3.1 Registration Card
        self.reg_frame = self.create_card()
        rlay = QVBoxLayout(self.reg_frame)
        rlay.setContentsMargins(20, 20, 20, 20)
        
        lbl_reg_title = QLabel("1. Frais d'Inscription / رسوم التسجيل")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            lbl_reg_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; border-bottom: 1px solid {colors.BORDER}; padding-bottom: 5px;")
        
        self.lbl_reg_status = QLabel("Statut: ...")
        self.lbl_reg_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if THEME_AVAILABLE:
            self.lbl_reg_status.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {ThemeManager.get_colors().TEXT_SECONDARY}; margin: 15px 0;")
        
        self.btn_pay_reg = QPushButton("Payer Inscription")
        self.btn_pay_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pay_reg.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.btn_pay_reg.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.WARNING}; color: white; font-weight: bold; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
                QPushButton:disabled {{ background-color: {colors.BORDER}; color: {colors.TEXT_SECONDARY}; }}
            """)
        self.btn_pay_reg.clicked.connect(self.pay_registration)
        
        rlay.addWidget(lbl_reg_title)
        rlay.addWidget(self.lbl_reg_status)
        rlay.addWidget(self.btn_pay_reg)
        rlay.addStretch()
        
        # 3.2 Monthly Grid Card
        self.month_frame = self.create_card()
        mlay = QVBoxLayout(self.month_frame)
        mlay.setContentsMargins(20, 20, 20, 20)
        
        lbl_month_title = QLabel("2. Mensualités / الأقساط الشهرية")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            lbl_month_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; border-bottom: 1px solid {colors.BORDER}; padding-bottom: 5px;")
        mlay.addWidget(lbl_month_title)
        
        self.month_grid = QGridLayout()
        self.month_grid.setSpacing(10)
        mlay.addLayout(self.month_grid)
        
        pay_layout.addWidget(self.reg_frame, 1)
        pay_layout.addWidget(self.month_frame, 3)
        self.main_layout.addLayout(pay_layout)

        # 4. Calculation & Validation Bar
        action_card = self.create_card()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            action_card.setStyleSheet(f"""
                QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 12px; }}
                QLabel {{ color: {colors.HEADER_TEXT}; font-weight: bold; }}
            """)
        alay = QHBoxLayout(action_card)
        alay.setContentsMargins(20, 15, 20, 15)
        alay.setSpacing(20)
        
        self.lbl_total_due = QLabel("Total Dû: 0")
        if THEME_AVAILABLE:
            self.lbl_total_due.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().HEADER_TEXT};")
        
        self.spin_discount = self.styled_spinbox("Remise: ")
        self.spin_discount.valueChanged.connect(self.recalc_totals)
        
        self.spin_paid_amount = self.styled_spinbox("Versé: ")
        self.spin_paid_amount.valueChanged.connect(self.recalc_totals)
        
        self.lbl_balance = QLabel("Reste: 0")
        if THEME_AVAILABLE:
            self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().WARNING};")
        
        self.btn_validate_monthly = QPushButton("VALIDER LE PAIEMENT")
        self.btn_validate_monthly.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validate_monthly.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.btn_validate_monthly.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.SUCCESS}; color: white; font-weight: bold; 
                    font-size: 14px; border-radius: 6px; padding: 0 30px; border: none;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        self.btn_validate_monthly.clicked.connect(self.pay_monthly)
        
        alay.addWidget(self.lbl_total_due)
        alay.addWidget(self.spin_discount)
        alay.addWidget(self.spin_paid_amount)
        alay.addWidget(self.lbl_balance)
        alay.addStretch()
        alay.addWidget(self.btn_validate_monthly)
        
        self.main_layout.addWidget(action_card)

        # 5. History Table
        self.table_history = QTableWidget()
        self.style_table(self.table_history)
        self.table_history.setColumnCount(6)
        self.table_history.setHorizontalHeaderLabels(["ID", "Date", "Type", "Total", "Versé", "Reçu"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.main_layout.addWidget(self.table_history)

        # Init Data
        self.month_checkboxes = {}
        self.academic_months = [
            (10, "Oct"), (11, "Nov"), (12, "Déc"), (1, "Jan"), (2, "Fév"), 
            (3, "Mars"), (4, "Avr"), (5, "Mai"), (6, "Juin")
        ]
        self.current_total_due = 0.0

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
        combo.setMinimumHeight(40)
        return combo

    def styled_spinbox(self, prefix):
        sb = QDoubleSpinBox()
        sb.setRange(0, 1000000)
        sb.setPrefix(prefix)
        sb.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            sb.setStyleSheet(f"""
                QDoubleSpinBox {{
                    padding: 8px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                    font-weight: bold;
                }}
            """)
        sb.setMinimumHeight(40)
        sb.setFixedWidth(150)
        return sb

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

    # --- Logic Methods ---
    def show_late_payers(self):
        dlg = LatePayersDialog(self)
        dlg.exec()

    def load_classes(self):
        self.combo_classes.clear()
        self.combo_classes.addItem("- Choisir Classe -", None)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, class_name_fr FROM Classes")
            for c in cursor.fetchall(): self.combo_classes.addItem(c[1], c[0])

    def load_students(self):
        cid = self.combo_classes.currentData()
        self.combo_students.clear()
        if not cid: return
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, first_name_fr || ' ' || last_name_fr FROM Students WHERE class_id=?", (cid,))
            for s in cursor.fetchall(): self.combo_students.addItem(s[1], s[0])

    def load_student_status(self):
        self.clear_month_grid()
        self.reset_calcs()
        sid = self.combo_students.currentData()
        cid = self.combo_classes.currentData()
        if not sid: return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Registration Check
            cursor.execute("SELECT amount FROM RegistrationFees WHERE class_id=?", (cid,))
            reg_res = cursor.fetchone()
            reg_amt = reg_res[0] if reg_res else 0.0
            
            cursor.execute("SELECT COUNT(*) FROM Payments WHERE student_id=? AND payment_type='Registration'", (sid,))
            is_reg = cursor.fetchone()[0] > 0
            
            if is_reg:
                self.lbl_reg_status.setText("✅ Inscrit / مسجل")
                if THEME_AVAILABLE:
                    self.lbl_reg_status.setStyleSheet(f"color: {ThemeManager.get_colors().SUCCESS}; font-weight: bold; font-size: 16px;")
                self.btn_pay_reg.setEnabled(False)
            else:
                self.lbl_reg_status.setText(f"❌ Non Payé: {reg_amt:,.0f} FCFA")
                if THEME_AVAILABLE:
                    self.lbl_reg_status.setStyleSheet(f"color: {ThemeManager.get_colors().DANGER}; font-weight: bold; font-size: 16px;")
                self.btn_pay_reg.setEnabled(True)
                self.btn_pay_reg.setProperty("amount", reg_amt)

            # Monthly Schedule
            cursor.execute("SELECT month_index, amount FROM MonthlyFeeSchedule WHERE class_id=?", (cid,))
            schedule = {r[0]: r[1] for r in cursor.fetchall()}
            
            cursor.execute("SELECT month_index FROM MonthlyPaymentsStatus WHERE student_id=?", (sid,))
            paid_months = [r[0] for r in cursor.fetchall()]

            # Build Grid
        row, col = 0, 0
        for m_idx, m_name in self.academic_months:
            amt = schedule.get(m_idx, 0.0)
            is_paid = m_idx in paid_months
            
            # Styled Month Box
            frame = QFrame()
            # Green for paid, Light Red/Pink for unpaid but due (simplified logic here: red for unpaid)
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                bg_color = self._rgba(colors.SUCCESS, 35) if is_paid else self._rgba(colors.DANGER, 35)
                border_color = colors.SUCCESS if is_paid else colors.DANGER
            
            frame.setStyleSheet(f"""
                QFrame {{ 
                    background-color: {bg_color}; 
                    border: 1px solid {border_color}; 
                    border-radius: 8px; 
                }}
            """)
            vb = QVBoxLayout(frame)
            vb.setContentsMargins(5, 5, 5, 5)
            
            status_icon = "✅" if is_paid else "⏳"
            lbl = QLabel(f"{m_name}\n{amt:.0f}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if THEME_AVAILABLE:
                lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 12px;")
            
            chk = QCheckBox(status_icon)
            chk.setEnabled(not is_paid)
            if is_paid: 
                chk.setChecked(True)
            else: 
                chk.stateChanged.connect(self.update_selection_total)
                self.month_checkboxes[m_idx] = (chk, amt)
            
            vb.addWidget(lbl)
            vb.addWidget(chk, 0, Qt.AlignmentFlag.AlignCenter)
            self.month_grid.addWidget(frame, row, col)
            
            col += 1
            if col > 2: col=0; row+=1
            
        self.load_history(sid)
        conn.close()

    def clear_month_grid(self):
        for i in reversed(range(self.month_grid.count())): 
            self.month_grid.itemAt(i).widget().setParent(None)
        self.month_checkboxes = {}

    def reset_calcs(self):
        self.spin_discount.setValue(0)
        self.spin_paid_amount.setValue(0)
        self.lbl_total_due.setText("Total Dû: 0")
        self.lbl_balance.setText("Reste: 0")
        self.current_total_due = 0.0

    def update_selection_total(self):
        total = 0.0
        for _, (chk, amt) in self.month_checkboxes.items():
            if chk.isChecked(): total += amt
        
        self.current_total_due = total
        self.lbl_total_due.setText(f"Total: {total:,.0f}")
        self.spin_paid_amount.setValue(total) 
        self.recalc_totals()

    def recalc_totals(self):
        discount = self.spin_discount.value()
        paid = self.spin_paid_amount.value()
        
        to_pay = max(0, self.current_total_due - discount)
        balance = to_pay - paid
        
        self.lbl_balance.setText(f"Reste: {balance:,.0f}")
        
        if balance > 0:
            if THEME_AVAILABLE:
                self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().DANGER};")
        elif balance < 0:
            if THEME_AVAILABLE:
                self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().PRIMARY};")
        else:
            if THEME_AVAILABLE:
                self.lbl_balance.setStyleSheet(f"font-size: 16px; color: {ThemeManager.get_colors().SUCCESS};")

    def pay_registration(self):
        sid = self.combo_students.currentData()
        amt = self.btn_pay_reg.property("amount")
        if not sid: return
        self.execute_payment(sid, amt, 0, amt, "Registration", "Frais d'inscription")

    def pay_monthly(self):
        sid = self.combo_students.currentData()
        if self.current_total_due <= 0: return
        
        discount = self.spin_discount.value()
        paid = self.spin_paid_amount.value()
        balance = (self.current_total_due - discount) - paid
        
        selected_months_indices = []
        selected_months_names = []
        
        for m_idx, (chk, _) in self.month_checkboxes.items():
            if chk.isChecked():
                selected_months_indices.append(m_idx)
                name = next((n for i, n in self.academic_months if i == m_idx), "")
                selected_months_names.append(name)
        
        desc = "Mois: " + ", ".join(selected_months_names)
        
        pid = self.execute_payment(sid, self.current_total_due, discount, paid, "Monthly", desc, balance)
        
        if pid:
            db = DatabaseManager()
            with db.get_connection() as conn:
                for m_idx in selected_months_indices:
                    amt = self.month_checkboxes[m_idx][1]
                    conn.execute("INSERT INTO MonthlyPaymentsStatus (student_id, month_index, payment_id, amount_paid) VALUES (?,?,?,?)",
                                 (sid, m_idx, pid, amt))
                conn.commit()
            self.load_student_status()

    def execute_payment(self, sid, total, discount, paid, ptype, details, balance=0):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                cursor.execute("""
                    INSERT INTO Payments (student_id, transaction_date, total_due, discount, amount_paid, remaining_balance, payment_type, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (sid, dt, total, discount, paid, balance, ptype, details))
                
                pid = cursor.lastrowid
                conn.commit()
            
            self.generate_receipt(pid)
            QMessageBox.information(self, "Succès", f"Paiement validé. Reçu N° {pid}")
            return pid
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return None

    def load_history(self, sid):
        self.table_history.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, transaction_date, payment_type, total_due, amount_paid FROM Payments WHERE student_id=? ORDER BY id DESC", (sid,))
            rows = cursor.fetchall()
            
        for row in rows:
            idx = self.table_history.rowCount()
            self.table_history.insertRow(idx)
            for i in range(5):
                self.table_history.setItem(idx, i, QTableWidgetItem(str(row[i])))
            
            btn = QPushButton("📄 Reçu")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                btn.setStyleSheet(f"background-color: {colors.PRIMARY}; color: white; border-radius: 4px; padding: 2px;")
            btn.clicked.connect(lambda ch, p=row[0]: self.generate_receipt(p))
            self.table_history.setCellWidget(idx, 5, btn)

    def generate_receipt(self, pid):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT P.id, P.transaction_date, S.first_name_fr, C.class_name_fr, 
                    P.total_due, P.discount, P.amount_paid, P.remaining_balance, P.details
                FROM Payments P
                JOIN Students S ON P.student_id = S.id
                JOIN Classes C ON S.class_id = C.id
                WHERE P.id=?
            """, (pid,))
            data = cursor.fetchone()
        
        if not data: return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "RECU DE PAIEMENT", 0, 1, 'C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"No: {data[0]} | Date: {data[1]}", 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, f"ELEVE: {sanitize(data[2])}", 0, 1)
        pdf.cell(0, 8, f"CLASSE: {sanitize(data[3])}", 0, 1)
        pdf.ln(5)
        
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(100, 10, "Description", 1, 0, 'C', True)
        pdf.cell(40, 10, "Valeur", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(100, 10, sanitize(data[8]), 1)
        pdf.cell(40, 10, f"{data[4]:,.0f}", 1, 1, 'R')
        
        if data[5] > 0:
            pdf.cell(100, 10, "Remise (Discount)", 1)
            pdf.cell(40, 10, f"-{data[5]:,.0f}", 1, 1, 'R')

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(100, 12, "NET PAYE (VERSE)", 1)
        pdf.cell(40, 12, f"{data[6]:,.0f} FCFA", 1, 1, 'R')
        
        if data[7] > 0:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(100, 10, "RESTE A PAYER (DETTE)", 1)
            pdf.cell(40, 10, f"{data[7]:,.0f} FCFA", 1, 1, 'R')
            pdf.set_text_color(0)

        default_name = f"Recu_{pid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Enregistrer le reçu", default_name, "PDF Files (*.pdf)")
        if not file_path:
            return

        pdf.output(file_path)
        if os.name == 'nt': os.startfile(file_path)
        else: subprocess.call(('xdg-open', file_path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentPaymentWindow()
    window.show()
    sys.exit(app.exec())