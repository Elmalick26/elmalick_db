import sys
import sqlite3
from database_setup import DatabaseManager
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QComboBox, QMessageBox, 
                             QHeaderView, QGroupBox, QDoubleSpinBox, QTabWidget,
                             QFrame, QGridLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from ui_styles import ThemeManager, Colors, get_table_style, get_tabs_style, get_card_style, apply_shadow_to_widget

THEME_AVAILABLE = True

class FeesSetupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Financière / الإعداد المالي")
        self.setMinimumSize(1100, 700)
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            # تطبيق نمط Deep Slate
            self.setStyleSheet(f"""
                QMainWindow {
                    background-color: {colors.BG_MAIN};
                }
                QLabel {
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }
                QGroupBox {
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: {colors.BG_CARD};
                    font-weight: bold;
                    color: {colors.TEXT_SECONDARY};
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    left: 10px;
                }
            """)
        
        # self.init_db() - centralized
        self.init_ui()
        self.load_classes()

    # init_db logic removed - handled in database_setup.py

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. Header Frame
        header_frame = QFrame()
        bg_header = ThemeManager.get_colors().BG_HEADER

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
        
        icon_lbl = QLabel("⚙️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("CONFIGURATION FINANCIÈRE")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {Colors().HEADER_TEXT}; background: transparent;")

        sub_lbl = QLabel("إعداد رسوم التسجيل وجدولة الأقساط الشهرية")
        sub_lbl.setFont(QFont("Cairo", 11))
        if THEME_AVAILABLE:
            sub_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().TEXT_SECONDARY}; background: transparent;")
        else:
            sub_lbl.setStyleSheet(f"color: {Colors().TEXT_SECONDARY}; background: transparent;")

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

        self.setup_registration_tab()
        self.setup_monthly_tab()

        self.main_layout.addWidget(self.tabs)

    def create_card(self):
        frame = QFrame()
        if THEME_AVAILABLE:
            frame.setStyleSheet(get_card_style())
            apply_shadow_to_widget(frame)
        else:
            colors = Colors()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_CARD};
                    border-radius: 12px;
                    border: 1px solid {colors.BORDER};
                }}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(15, 23, 42, 15))
            shadow.setOffset(0, 4)
            frame.setGraphicsEffect(shadow)
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
        else:
            colors = Colors()
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

    def styled_spinbox(self):
        sb = QDoubleSpinBox()
        sb.setRange(0, 1000000)
        sb.setPrefix("FCFA ")
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
                QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            sb.setStyleSheet(f"""
                QDoubleSpinBox {
                    padding: 8px 12px;
                    border: 1px solid {colors.BORDER};
                    border-radius: 6px;
                    background: {colors.INPUT_BG};
                    color: {colors.TEXT_PRIMARY};
                    font-weight: bold;
                }
                QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        sb.setMinimumHeight(40)
        return sb

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())

    # ============================================
    # TAB 1: REGISTRATION FEES
    # ============================================
    def setup_registration_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Control Card
        reg_card = self.create_card()
        hlay = QHBoxLayout(reg_card)
        hlay.setContentsMargins(20, 20, 20, 20)
        hlay.setSpacing(15)
        
        self.combo_class_reg = self.styled_combo()
        self.spin_reg_amount = self.styled_spinbox()
        
        btn_save_reg = QPushButton("Enregistrer")
        btn_save_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        colors = ThemeManager.get_colors()
        btn_save_reg.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {colors.PRIMARY}; color: white; font-weight: bold; 
                border-radius: 6px; padding: 10px 20px; border: none;
            }}
            QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
        """)
        btn_save_reg.clicked.connect(self.save_registration_fee)
        
        hlay.addWidget(QLabel("Classe:"))
        hlay.addWidget(self.combo_class_reg, 1)
        hlay.addWidget(QLabel("Montant:"))
        hlay.addWidget(self.spin_reg_amount, 1)
        hlay.addWidget(btn_save_reg)
        
        layout.addWidget(reg_card)
        
        # Table
        self.table_reg = QTableWidget(0, 2)
        self.style_table(self.table_reg)
        self.table_reg.setHorizontalHeaderLabels(["Classe / الفصل", "Montant Inscription / مبلغ التسجيل"])
        self.table_reg.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_reg)
        
        self.tabs.addTab(tab, "  📝 Inscription / التسجيل  ")

    # ============================================
    # TAB 2: MONTHLY FEE SCHEDULE
    # ============================================
    def setup_monthly_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 1. Class Selection Card
        sel_card = self.create_card()
        slay = QHBoxLayout(sel_card)
        slay.setContentsMargins(20, 20, 20, 20)
        
        self.combo_class_month = self.styled_combo()
        self.combo_class_month.currentIndexChanged.connect(self.load_monthly_schedule)
        
        slay.addWidget(QLabel("Configurer pour la classe:"))
        slay.addWidget(self.combo_class_month, 1)
        layout.addWidget(sel_card)

        # 2. Smart Tool Card (Distinct Style)
        tool_frame = QFrame()
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            tool_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.BG_CARD};
                    border: 1px dashed {colors.SUCCESS}; 
                    border-radius: 8px;
                }}
                QLabel {{ color: {colors.TEXT_PRIMARY}; font-weight: bold; }}
            """)
        tool_layout = QVBoxLayout(tool_frame)
        
        tool_header = QLabel("⚡ Outil de Calcul Rapide / أداة الحساب السريع")
        tool_layout.addWidget(tool_header)
        
        tlay = QHBoxLayout()
        self.spin_base_price = self.styled_spinbox()
        self.spin_base_price.setValue(5000)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.spin_base_price.setStyleSheet(f"""
                QDoubleSpinBox {{ background: {colors.INPUT_BG}; border: 1px solid {colors.SUCCESS}; border-radius: 4px; padding: 5px; color: {colors.TEXT_PRIMARY}; }}
                QDoubleSpinBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            self.spin_base_price.setStyleSheet(
                f"QDoubleSpinBox {{ background: {colors.INPUT_BG}; border: 1px solid {colors.SUCCESS}; border-radius: 4px; padding: 5px; color: {colors.TEXT_PRIMARY}; }}"
            )
        
        btn_apply_smart = QPushButton("Répartition 4+4 (Smart)")
        btn_apply_smart.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_apply_smart.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; border-radius: 4px; padding: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_apply_smart.clicked.connect(self.apply_smart_distribution)
        
        btn_apply_flat = QPushButton("Prix Unique (Flat)")
        btn_apply_flat.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_apply_flat.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY_DARK}; color: white; font-weight: bold; border-radius: 4px; padding: 8px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_apply_flat.clicked.connect(self.apply_flat_distribution)
        
        tlay.addWidget(QLabel("Prix de base:"))
        tlay.addWidget(self.spin_base_price)
        tlay.addWidget(btn_apply_smart)
        tlay.addWidget(btn_apply_flat)
        tool_layout.addLayout(tlay)
        
        layout.addWidget(tool_frame)

        # 3. Schedule Table
        self.table_months = QTableWidget(9, 2)
        self.style_table(self.table_months)
        self.table_months.setHorizontalHeaderLabels(["Mois / الشهر", "Montant à Payer (FCFA)"])
        self.table_months.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_months.verticalHeader().setDefaultSectionSize(40)
        
        self.academic_months = [
            (10, "Octobre / أكتوبر"), (11, "Novembre / نوفمبر"), (12, "Décembre / ديسمبر"), 
            (1, "Janvier / يناير"), (2, "Février / فبراير"), (3, "Mars / مارس"), 
            (4, "Avril / أبريل"), (5, "Mai / مايو"), (6, "Juin / يونيو")
        ]
        
        for i, (idx, name) in enumerate(self.academic_months):
            self.table_months.setItem(i, 0, QTableWidgetItem(name))
            sp = QDoubleSpinBox()
            sp.setRange(0, 100000)
            sp.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            if THEME_AVAILABLE:
                sp.setStyleSheet(f"background: transparent; border: none; font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY};")
            self.table_months.setCellWidget(i, 1, sp)
            
        layout.addWidget(self.table_months)

        # 4. Save Button
        btn_save_schedule = QPushButton("💾 ENREGISTRER L'ÉCHÉANCIER")
        btn_save_schedule.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_schedule.setMinimumHeight(50)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_save_schedule.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; 
                    font-weight: bold; font-size: 14px; border-radius: 8px; border: none;
                }}
                QPushButton:hover {{ background-color: {colors.BORDER}; color: {colors.TEXT_PRIMARY}; }}
            """)
        btn_save_schedule.clicked.connect(self.save_monthly_schedule)
        layout.addWidget(btn_save_schedule)

        self.tabs.addTab(tab, "  📅 Mensualités / الأقساط الشهرية  ")

    # --- Logic ---
    def load_classes(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, class_name_fr FROM Classes")
            classes = cursor.fetchall()
            
            self.combo_class_reg.clear()
            self.combo_class_month.clear()
            self.combo_class_reg.addItem("- Choisir -", None)
            self.combo_class_month.addItem("- Choisir -", None)
            
            for c in classes:
                self.combo_class_reg.addItem(c[1], c[0])
                self.combo_class_month.addItem(c[1], c[0])
        
        self.load_reg_table()

    # --- Registration Logic ---
    def save_registration_fee(self):
        class_id = self.combo_class_reg.currentData()
        amount = self.spin_reg_amount.value()
        
        if not class_id: return
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM RegistrationFees WHERE class_id=?", (class_id,))
            cursor.execute("INSERT INTO RegistrationFees (class_id, amount) VALUES (?,?)", (class_id, amount))
            conn.commit()
        self.load_reg_table()
        QMessageBox.information(self, "Succès", "Frais d'inscription mis à jour.")

    def load_reg_table(self):
        self.table_reg.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT C.class_name_fr, R.amount 
                FROM RegistrationFees R JOIN Classes C ON R.class_id = C.id
            """)
            for r in cursor.fetchall():
                idx = self.table_reg.rowCount()
                self.table_reg.insertRow(idx)
                self.table_reg.setItem(idx, 0, QTableWidgetItem(r[0]))
                self.table_reg.setItem(idx, 1, QTableWidgetItem(f"{r[1]:,.0f} FCFA"))

    # --- Monthly Logic ---
    def apply_smart_distribution(self):
        base = self.spin_base_price.value()
        extra = base / 4
        for i in range(9):
            sp = self.table_months.cellWidget(i, 1)
            if i < 4: sp.setValue(base)
            elif i < 8: sp.setValue(base + extra)
            else: sp.setValue(0)

    def apply_flat_distribution(self):
        base = self.spin_base_price.value()
        for i in range(9): self.table_months.cellWidget(i, 1).setValue(base)

    def save_monthly_schedule(self):
        class_id = self.combo_class_month.currentData()
        if not class_id: 
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner une classe.")
            return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM MonthlyFeeSchedule WHERE class_id=?", (class_id,))
            
            for i, (month_idx, month_name) in enumerate(self.academic_months):
                amount = self.table_months.cellWidget(i, 1).value()
                cursor.execute("""
                    INSERT INTO MonthlyFeeSchedule (class_id, month_index, month_name, amount)
                    VALUES (?, ?, ?, ?)
                """, (class_id, month_idx, month_name, amount))
            
            conn.commit()
        QMessageBox.information(self, "Succès", "Échéancier enregistré avec succès.")

    def load_monthly_schedule(self):
        class_id = self.combo_class_month.currentData()
        for i in range(9): self.table_months.cellWidget(i, 1).setValue(0)
        
        if not class_id: return
        
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT month_index, amount FROM MonthlyFeeSchedule WHERE class_id=?", (class_id,))
            rows = cursor.fetchall()
        
        data_map = {r[0]: r[1] for r in rows}
        
        for i, (m_idx, _) in enumerate(self.academic_months):
            if m_idx in data_map:
                self.table_months.cellWidget(i, 1).setValue(data_map[m_idx])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FeesSetupWindow()
    window.show()
    sys.exit(app.exec())