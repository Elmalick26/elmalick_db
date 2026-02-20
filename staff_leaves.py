import sys
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QComboBox, QMessageBox, 
                             QHeaderView, QGroupBox, QDateEdit, QTextEdit,
                             QTabWidget, QFrame, QGraphicsDropShadowEffect, QGridLayout)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from database_setup import DatabaseManager

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True

class StaffLeaveWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des Congés / إدارة الإجازات")
        self.setMinimumSize(1100, 750)
        
        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            # تطبيق نمط Deep Slate
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-color: {colors.BG_MAIN};
                }}
                QLabel {{
                    font-family: 'Segoe UI', 'Cairo', sans-serif;
                    color: {colors.TEXT_PRIMARY};
                }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER};
                    border-radius: 8px;
                    margin-top: 10px;
                    background-color: {colors.BG_CARD};
                    font-weight: bold;
                    color: {colors.TEXT_SECONDARY};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 5px;
                    left: 10px;
                }}
            """)
        
        self.init_ui()
        self.load_staff()
        self.load_leaves()


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
            QFrame {{
                background-color: {colors.BG_HEADER};
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
        
        icon_lbl = QLabel("🏖️")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DES CONGÉS")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إدارة الإجازات والغيابات للموظفين")
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
            colors = Colors()
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
                    background: {colors.BG_HEADER}; 
                    color: {colors.HEADER_TEXT}; 
                }}
                QTabBar::tab:hover {{
                    background: {colors.BORDER}; 
                }}
            """)
        
        self.setup_request_tab()
        self.setup_history_tab()
        
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

    def styled_date(self):
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setMinimumHeight(38)
        return de

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(38)
        return combo

    def style_table(self, table):
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        if THEME_AVAILABLE:
            table.setStyleSheet(get_table_style())
        else:
            colors = Colors()
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

    def setup_request_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form Card
        form_card = self.create_card()
        flay = QGridLayout(form_card)
        flay.setSpacing(15)
        flay.setContentsMargins(20, 20, 20, 20)
        
        # Title inside card
        card_title = QLabel("📝 Nouvelle Demande / طلب جديد")
        if THEME_AVAILABLE:
            card_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        else:
            card_title.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        flay.addWidget(card_title, 0, 0, 1, 4)
        
        self.combo_staff = self.styled_combo()
        self.combo_type = self.styled_combo()
        self.combo_type.addItems(["Maladie (مرضية)", "Annuel (سنوية)", "Sans Solde (بدون راتب)", "Maternité (أمومة)", "Urgence (طارئة)"])
        
        flay.addWidget(QLabel("Employé:"), 1, 0)
        flay.addWidget(self.combo_staff, 1, 1)
        flay.addWidget(QLabel("Type:"), 1, 2)
        flay.addWidget(self.combo_type, 1, 3)
        
        self.date_start = self.styled_date()
        self.date_start.setDate(QDate.currentDate())
        
        self.date_end = self.styled_date()
        self.date_end.setDate(QDate.currentDate())
        
        self.lbl_days = QLabel("⏱️ Durée: 1 jour(s)")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.lbl_days.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};")
        else:
            colors = Colors()
            self.lbl_days.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};")
        self.lbl_days.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.date_start.dateChanged.connect(self.calculate_days)
        self.date_end.dateChanged.connect(self.calculate_days)

        flay.addWidget(QLabel("Du:"), 2, 0)
        flay.addWidget(self.date_start, 2, 1)
        flay.addWidget(QLabel("Au:"), 2, 2)
        flay.addWidget(self.date_end, 2, 3)
        
        flay.addWidget(self.lbl_days, 3, 0, 1, 4)
        
        self.txt_reason = QTextEdit()
        self.txt_reason.setPlaceholderText("Motif de l'absence / سبب الإجازة...")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.txt_reason.setStyleSheet(f"""
                QTextEdit {{ 
                    padding: 10px; 
                    border: 1px solid {colors.BORDER}; 
                    border-radius: 6px; 
                    background: {colors.INPUT_BG}; 
                    color: {colors.TEXT_PRIMARY}; 
                }}
                QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        else:
            colors = Colors()
            self.txt_reason.setStyleSheet(f"""
                QTextEdit {{ 
                    padding: 10px; 
                    border: 1px solid {colors.BORDER}; 
                    border-radius: 6px; 
                    background: {colors.INPUT_BG}; 
                    color: {colors.TEXT_PRIMARY}; 
                }}
                QTextEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}
            """)
        self.txt_reason.setMaximumHeight(100)
        
        flay.addWidget(QLabel("Motif:"), 4, 0)
        flay.addWidget(self.txt_reason, 4, 1, 1, 3)
        
        btn_save = QPushButton("✅ Enregistrer la Demande / حفظ الطلب")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setMinimumHeight(45)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_save.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.SUCCESS}; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 8px; 
                    border: none;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_save.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.SUCCESS}; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 8px; 
                    border: none;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_save.clicked.connect(self.save_leave)
        
        flay.addWidget(btn_save, 5, 0, 1, 4)
        
        layout.addWidget(form_card)
        layout.addStretch()
        self.tabs.addTab(tab, "  ➕ Nouvelle Demande / طلب جديد  ")

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Control bar
        toolbar = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_refresh.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    padding: 8px 15px;
                    border-radius: 6px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_refresh.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {colors.PRIMARY}; 
                    color: white; 
                    font-weight: bold; 
                    padding: 8px 15px;
                    border-radius: 6px; 
                    border: none;
                }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_refresh.clicked.connect(self.load_leaves)
        
        toolbar.addWidget(QLabel("Historique des Demandes / سجل الطلبات"))
        toolbar.addStretch()
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)
        
        self.table_leaves = QTableWidget()
        self.style_table(self.table_leaves)
        self.table_leaves.setColumnCount(8)
        self.table_leaves.setHorizontalHeaderLabels(["ID", "Employé", "Type", "Début", "Fin", "Jours", "Statut", "Action"])
        self.table_leaves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_leaves.setColumnWidth(0, 50)
        self.table_leaves.setColumnWidth(7, 180)
        
        layout.addWidget(self.table_leaves)
        self.tabs.addTab(tab, "  📋 Historique & Validation / السجل  ")

    def load_staff(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, first_name || ' ' || last_name FROM Staff WHERE status='Actif'")
            rows = cursor.fetchall()
        for row in rows:
            self.combo_staff.addItem(row[1], row[0])

    def calculate_days(self):
        d1 = self.date_start.date()
        d2 = self.date_end.date()
        days = d1.daysTo(d2) + 1
        if days < 1:
            self.lbl_days.setText("Erreur: Date invalide")
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                self.lbl_days.setStyleSheet(f"color: {colors.DANGER}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.DANGER};")
            else:
                colors = Colors()
                self.lbl_days.setStyleSheet(f"color: {colors.DANGER}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.DANGER};")
        else:
            self.lbl_days.setText(f"Durée: {days} jour(s)")
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                self.lbl_days.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};")
            else:
                colors = Colors()
                self.lbl_days.setStyleSheet(f"color: {colors.PRIMARY}; font-weight: bold; background-color: {colors.BG_MAIN}; padding: 10px; border-radius: 6px; border: 1px solid {colors.BORDER};")

    def save_leave(self):
        staff_id = self.combo_staff.currentData()
        l_type = self.combo_type.currentText().split(" ")[0] 
        d1 = self.date_start.date()
        d2 = self.date_end.date()
        days = d1.daysTo(d2) + 1
        reason = self.txt_reason.toPlainText()

        if days < 1:
            QMessageBox.warning(self, "Erreur", "La date de fin doit être après la date de début.")
            return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO StaffLeaves (staff_id, leave_type, start_date, end_date, days_count, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (staff_id, l_type, d1.toString("yyyy-MM-dd"), d2.toString("yyyy-MM-dd"), days, reason))
            conn.commit()
        
        QMessageBox.information(self, "Succès", "Demande de congé enregistrée.")
        self.txt_reason.clear()
        self.load_leaves()
        self.tabs.setCurrentIndex(1) 

    def load_leaves(self):
        self.table_leaves.setRowCount(0)
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT L.id, S.first_name || ' ' || S.last_name, L.leave_type, 
                    L.start_date, L.end_date, L.days_count, L.status
                FROM StaffLeaves L
                JOIN Staff S ON L.staff_id = S.id
                ORDER BY L.start_date DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
        
        for r in rows:
            idx = self.table_leaves.rowCount()
            self.table_leaves.insertRow(idx)
            
            for i in range(7):
                item = QTableWidgetItem(str(r[i]))
                if i == 6: # Status
                    if r[i] == 'Approuvé': 
                        if THEME_AVAILABLE:
                            item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                        else:
                            item.setForeground(QColor(Colors().SUCCESS))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    elif r[i] == 'Rejeté': 
                        if THEME_AVAILABLE:
                            item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                        else:
                            item.setForeground(QColor(Colors().DANGER))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    else: 
                        if THEME_AVAILABLE:
                            item.setForeground(QColor(ThemeManager.get_colors().WARNING))
                        else:
                            item.setForeground(QColor(Colors().WARNING))
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table_leaves.setItem(idx, i, item)
            
            # Action Buttons
            if r[6] == 'En Attente':
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(2,2,2,2)
                btn_layout.setSpacing(5)
                
                btn_ok = QPushButton("✔")
                btn_ok.setFixedSize(30, 25)
                btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_ok.setToolTip("Approuver")
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    btn_ok.setStyleSheet(f"background-color: {colors.SUCCESS}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                else:
                    btn_ok.setStyleSheet(f"background-color: {Colors().SUCCESS}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                btn_ok.clicked.connect(lambda ch, lid=r[0]: self.update_status(lid, "Approuvé"))
                
                btn_no = QPushButton("✘")
                btn_no.setFixedSize(30, 25)
                btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_no.setToolTip("Rejeter")
                if THEME_AVAILABLE:
                    colors = ThemeManager.get_colors()
                    btn_no.setStyleSheet(f"background-color: {colors.DANGER}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                else:
                    btn_no.setStyleSheet(f"background-color: {Colors().DANGER}; color: white; border-radius: 4px; font-weight: bold; border: none;")
                btn_no.clicked.connect(lambda ch, lid=r[0]: self.update_status(lid, "Rejeté"))
                
                btn_layout.addWidget(btn_ok)
                btn_layout.addWidget(btn_no)
                btn_layout.addStretch()
                self.table_leaves.setCellWidget(idx, 7, btn_widget)
            else:
                self.table_leaves.setItem(idx, 7, QTableWidgetItem(""))

    def update_status(self, leave_id, new_status):
        db = DatabaseManager()
        with db.get_connection() as conn:
            conn.execute("UPDATE StaffLeaves SET status=? WHERE id=?", (new_status, leave_id))
            conn.commit()
        self.load_leaves()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StaffLeaveWindow()
    window.show()
    sys.exit(app.exec())