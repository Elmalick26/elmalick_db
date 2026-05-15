import sys
import sqlite3
import os
from datetime import datetime
from fpdf import FPDF
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QFrame, QDateEdit,
                             QTabWidget, QGridLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from database_setup import DatabaseManager
import security_utils
from print_export_service import output_pdf, get_report_output_mode
from pdf_report_style import apply_grades_sheet_header, apply_table_header_style, apply_table_body_style, set_zebra_row_fill, get_school_info_row

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True
USER_AUDIT_REPORT_OUTPUT_MODE = get_report_output_mode("user_audit_report_mode", "save")

def _get_arabic_font_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "fonts", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(base_dir, "fonts", "Cairo-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Amiri", "Amiri-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Noto_Naskh_Arabic", "NotoNaskhArabic-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "Cairo", "Cairo-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

class UserManagementWindow(QMainWindow):
    def __init__(self, current_user="Admin"):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Gestion des Utilisateurs / إدارة المستخدمين")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
            colors = Colors()
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {colors.BG_MAIN}; }}
                QLabel {{ font-family: 'Segoe UI', 'Cairo', sans-serif; color: {colors.TEXT_PRIMARY}; }}
                QGroupBox {{
                    border: 1px solid {colors.BORDER}; border-radius: 8px; margin-top: 10px;
                    background-color: {colors.BG_CARD}; font-weight: bold; color: {colors.TEXT_SECONDARY};
                }}
            """)

        self.selected_user_id = None
        self.selected_username = ""
        self.current_audit_report_rows = []
        self.current_audit_report_headers = ["Date/Heure", "Acteur", "Action", "Cible"]
        self.current_audit_report_title = "Rapport Journal d'Audit"
        self.current_audit_period_label = "30 derniers jours"

        self.ensure_admin_exists()
        self.init_ui()
        self.load_users()
        self.load_audit_logs()

    def ensure_admin_exists(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM Users")
                if cursor.fetchone()[0] == 0:
                    default_pass = security_utils.hash_password("admin")
                    cursor.execute("INSERT INTO Users (username, email, password_hash, role) VALUES (?, ?, ?, ?)", 
                                ("admin", "admin@school.local", default_pass, "Admin"))
                    cursor.execute("INSERT INTO AuditLogs (actor, action, target, timestamp) VALUES (?, ?, ?, ?)",
                                ("System", "Auto-Create", "admin", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
        except Exception as e:
            print(f"Error ensuring admin exists: {e}")

    def log_action(self, action, target):
        try:
            db = DatabaseManager()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with db.get_connection() as conn:
                conn.execute("INSERT INTO AuditLogs (actor, action, target, timestamp) VALUES (?, ?, ?, ?)",
                            (self.current_user, action, target, timestamp))
                conn.commit()
            self.load_audit_logs()
        except Exception as e:
            print(f"Audit Error: {e}")

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

        # 1. Header Frame
        header_frame = QFrame()
        header_frame.setStyleSheet(f"QFrame {{ background-color: {colors.BG_HEADER}; border-radius: 10px; }}")
        header_frame.setMaximumHeight(80)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        hl = QHBoxLayout(header_frame)
        hl.setContentsMargins(20, 15, 20, 15)
        
        icon_lbl = QLabel("🔐")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DES UTILISATEURS")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet(f"color: {colors.HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إدارة الصلاحيات، الحسابات، وسجل العمليات")
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
                QTabBar::tab:selected {{ background: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; }}
                QTabBar::tab:hover {{ background: {colors.BORDER}; }}
            """)
        
        self.setup_users_tab()
        self.setup_audit_tab()
        
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
        le.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        le.setStyleSheet(f"QLineEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QLineEdit:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
        return le

    def styled_combo(self):
        combo = QComboBox()
        combo.setMinimumHeight(38)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        combo.setStyleSheet(f"QComboBox {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }} QComboBox:focus {{ border: 2px solid {colors.BORDER_FOCUS}; background: {colors.INPUT_BG_FOCUS}; }}")
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
                QTableWidget {{ background-color: {colors.BG_CARD}; border: 1px solid {colors.BORDER}; border-radius: 8px; gridline-color: {colors.BORDER}; font-size: 13px; color: {colors.TEXT_PRIMARY}; }}
                QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {colors.BG_MAIN}; }}
                QTableWidget::item:selected {{ background-color: {colors.PRIMARY}; color: white; }}
                QHeaderView::section {{ background-color: {colors.BG_HEADER}; color: {colors.HEADER_TEXT}; padding: 10px; border: none; font-weight: bold; }}
            """)

    def setup_users_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Left Card: Add User
        add_card = self.create_card()
        alay = QVBoxLayout(add_card)
        alay.setContentsMargins(15, 15, 15, 15)
        
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        lbl_add_title = QLabel("➕ Nouveau Utilisateur / إضافة مستخدم")
        lbl_add_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        alay.addWidget(lbl_add_title)
        
        form_grid = QGridLayout()
        self.combo_staff = self.styled_combo()
        self.combo_staff.setPlaceholderText("Lier à un employé...")
        self.load_staff_list()
        self.combo_staff.currentIndexChanged.connect(self.on_staff_selected)
        
        self.txt_new_user = self.styled_input("Nom d'utilisateur")
        self.txt_new_email = self.styled_input("Email")
        self.txt_new_pass = self.styled_input("Mot de passe")
        self.txt_new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.combo_role = self.styled_combo()
        self.combo_role.addItems(["Admin", "Comptable", "Prof", "Secretaire", "Pédagogique"])
        
        form_grid.addWidget(QLabel("Employé:"), 0, 0)
        form_grid.addWidget(self.combo_staff, 0, 1)
        form_grid.addWidget(QLabel("Rôle:"), 1, 0)
        form_grid.addWidget(self.combo_role, 1, 1)
        form_grid.addWidget(QLabel("User:"), 2, 0)
        form_grid.addWidget(self.txt_new_user, 2, 1)
        form_grid.addWidget(QLabel("Email:"), 3, 0)
        form_grid.addWidget(self.txt_new_email, 3, 1)
        form_grid.addWidget(QLabel("Pass:"), 4, 0)
        form_grid.addWidget(self.txt_new_pass, 4, 1)
        
        btn_add = QPushButton("Créer le compte")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}")
        btn_add.clicked.connect(self.add_user)
        
        alay.addLayout(form_grid)
        alay.addWidget(btn_add)
        alay.addStretch()
        
        top_layout.addWidget(add_card, 1)

        # Right Card: Manage Selected User
        manage_card = self.create_card()
        mlay = QVBoxLayout(manage_card)
        mlay.setContentsMargins(15, 15, 15, 15)
        
        lbl_manage_title = QLabel("🔧 Gestion & Sécurité / إدارة الحساب")
        lbl_manage_title.setStyleSheet(f"font-weight: bold; color: {colors.TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        mlay.addWidget(lbl_manage_title)
        
        self.lbl_selected_user = QLabel("Aucun utilisateur sélectionné")
        self.lbl_selected_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 8px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER};")
        mlay.addWidget(self.lbl_selected_user)
        
        mlay.addSpacing(10)
        mlay.addWidget(QLabel("Réinitialiser le mot de passe:"))
        self.txt_reset_pass = self.styled_input("Nouveau mot de passe")
        self.txt_reset_pass.setEchoMode(QLineEdit.EchoMode.Password)
        mlay.addWidget(self.txt_reset_pass)
        
        btn_reset = QPushButton("Modifier le Mot de Passe")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_reset.clicked.connect(self.reset_password)
        mlay.addWidget(btn_reset)
        
        mlay.addSpacing(15)
        btn_delete = QPushButton("Supprimer ce Compte")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(f"QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; padding: 8px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}")
        btn_delete.clicked.connect(self.delete_user)
        mlay.addWidget(btn_delete)
        mlay.addStretch()
        
        top_layout.addWidget(manage_card, 1)
        layout.addLayout(top_layout)

        # Bottom Section: Users Table
        layout.addWidget(QLabel("Liste des Utilisateurs / قائمة المستخدمين:"))
        self.table = QTableWidget()
        self.style_table(self.table)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "👤 Employé", "📝 Utilisateur", "📧 Email", "🔐 Rôle"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemClicked.connect(self.select_user)
        
        layout.addWidget(self.table)
        self.tabs.addTab(tab, "  👥 Utilisateurs  ")

    def setup_audit_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        filter_card = self.create_card()
        flay = QHBoxLayout(filter_card)
        flay.setContentsMargins(10, 10, 10, 10)
        
        self.txt_audit_search = self.styled_input("🔍 Rechercher dans l'historique (Nom, Action, Date)...")
        self.txt_audit_search.textChanged.connect(self.load_audit_logs)
        flay.addWidget(self.txt_audit_search)

        self.combo_audit_period = self.styled_combo()
        self.combo_audit_period.addItems(["7 derniers jours", "30 derniers jours", "90 derniers jours", "Période personnalisée", "Tout"])
        self.combo_audit_period.setCurrentText("30 derniers jours")
        self.combo_audit_period.currentIndexChanged.connect(self.on_audit_period_changed)
        flay.addWidget(self.combo_audit_period)

        self.date_audit_from = QDateEdit()
        self.date_audit_from.setCalendarPopup(True)
        self.date_audit_from.setDisplayFormat("yyyy-MM-dd")
        self.date_audit_from.setDate(QDate.currentDate().addDays(-29))
        self.date_audit_from.setEnabled(False)
        self.date_audit_from.dateChanged.connect(self.load_audit_logs)
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.date_audit_from.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        flay.addWidget(self.date_audit_from)

        self.date_audit_to = QDateEdit()
        self.date_audit_to.setCalendarPopup(True)
        self.date_audit_to.setDisplayFormat("yyyy-MM-dd")
        self.date_audit_to.setDate(QDate.currentDate())
        self.date_audit_to.setEnabled(False)
        self.date_audit_to.dateChanged.connect(self.load_audit_logs)
        self.date_audit_to.setStyleSheet(f"QDateEdit {{ padding: 8px 12px; border: 1px solid {colors.BORDER}; border-radius: 6px; background: {colors.INPUT_BG}; color: {colors.TEXT_PRIMARY}; }}")
        flay.addWidget(self.date_audit_to)

        self.combo_audit_limit = self.styled_combo()
        self.combo_audit_limit.addItems(["100", "300", "500", "1000"])
        self.combo_audit_limit.setCurrentText("300")
        self.combo_audit_limit.currentIndexChanged.connect(self.load_audit_logs)
        flay.addWidget(self.combo_audit_limit)

        btn_export_audit = QPushButton("📄 Exporter Rapport PDF")
        btn_export_audit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_audit.setStyleSheet(f"QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}")
        btn_export_audit.clicked.connect(self.export_audit_report_pdf)
        flay.addWidget(btn_export_audit)
        
        layout.addWidget(filter_card)

        self.table_audit = QTableWidget()
        self.style_table(self.table_audit)
        self.table_audit.setColumnCount(4)
        self.table_audit.setHorizontalHeaderLabels(["Date/Heure", "Acteur (من)", "Action (ماذا)", "Cible (على من)"])
        self.table_audit.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_audit)
        
        self.tabs.addTab(tab, "  📜 Journal d'Audit / السجل  ")

    def on_audit_period_changed(self):
        is_custom = self.combo_audit_period.currentText() == "Période personnalisée"
        self.date_audit_from.setEnabled(is_custom)
        self.date_audit_to.setEnabled(is_custom)
        self.load_audit_logs()

    def get_audit_date_range(self):
        period = self.combo_audit_period.currentText()
        today = QDate.currentDate()

        if period == "7 derniers jours":
            self.current_audit_period_label = "7 derniers jours"
            start = today.addDays(-6).toString("yyyy-MM-dd") + " 00:00:00"
            end = today.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        if period == "30 derniers jours":
            self.current_audit_period_label = "30 derniers jours"
            start = today.addDays(-29).toString("yyyy-MM-dd") + " 00:00:00"
            end = today.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        if period == "90 derniers jours":
            self.current_audit_period_label = "90 derniers jours"
            start = today.addDays(-89).toString("yyyy-MM-dd") + " 00:00:00"
            end = today.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        if period == "Période personnalisée":
            start_date = self.date_audit_from.date()
            end_date = self.date_audit_to.date()
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            self.current_audit_period_label = f"{start_date.toString('yyyy-MM-dd')} -> {end_date.toString('yyyy-MM-dd')}"
            start = start_date.toString("yyyy-MM-dd") + " 00:00:00"
            end = end_date.toString("yyyy-MM-dd") + " 23:59:59"
            return start, end

        self.current_audit_period_label = "Tout"
        return None, None

    # --- Logic ---
    def load_staff_list(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, first_name, last_name FROM Staff WHERE status='Actif' ORDER BY last_name")
                rows = cursor.fetchall()
            
            self.combo_staff.clear()
            self.combo_staff.addItem("- Aucun lien -", None)
            
            for staff_id, first_name, last_name in rows:
                first = str(first_name or "").strip()
                last = str(last_name or "").strip()
                display_name = (f"{first} {last}".strip() or "[Staff]")
                self.combo_staff.addItem(display_name, staff_id)
        except: pass

    def on_staff_selected(self):
        staff_id = self.combo_staff.currentData()
        if not staff_id:
            self.txt_new_email.clear()
            return
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT email FROM Staff WHERE id=?", (staff_id,))
                row = cursor.fetchone()
            email = row[0] if row and row[0] else ""
            self.txt_new_email.setText(email)
        except Exception:
            self.txt_new_email.clear()

    def load_users(self):
        self.table.setRowCount(0)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT u.id, u.staff_id, 
                        COALESCE(s.first_name || ' ' || s.last_name, '---') as staff_name,
                        u.username, u.email, u.role 
                    FROM Users u 
                    LEFT JOIN Staff s ON u.staff_id = s.id
                    ORDER BY u.id DESC
                """)
                rows = cursor.fetchall()
            
            for row in rows:
                idx = self.table.rowCount()
                self.table.insertRow(idx)
                user_id, staff_id, staff_name, username, email, role = row
                self.table.setItem(idx, 0, QTableWidgetItem(str(user_id)))
                self.table.setItem(idx, 1, QTableWidgetItem(str(staff_name or "---")))
                self.table.setItem(idx, 2, QTableWidgetItem(str(username or "")))
                self.table.setItem(idx, 3, QTableWidgetItem(str(email or "")))
                self.table.setItem(idx, 4, QTableWidgetItem(str(role or "")))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de chargement: {e}")

    def load_audit_logs(self):
        self.table_audit.setRowCount(0)
        search = self.txt_audit_search.text()
        max_rows = int(self.combo_audit_limit.currentText()) if hasattr(self, "combo_audit_limit") else 300
        date_start, date_end = self.get_audit_date_range() if hasattr(self, "combo_audit_period") else (None, None)
        
        try:
            db = DatabaseManager()
            query = "SELECT timestamp, actor, action, target FROM AuditLogs WHERE (actor LIKE ? OR action LIKE ? OR target LIKE ?)"
            params = [f"%{search}%", f"%{search}%", f"%{search}%"]

            if date_start and date_end:
                query += " AND timestamp >= ? AND timestamp <= ?"
                params.extend([date_start, date_end])

            query += " ORDER BY id DESC LIMIT ?"
            params.append(max_rows)
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

            self.current_audit_report_rows = [[r[0], r[1], r[2], r[3]] for r in rows]

            colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()

            for row in rows:
                idx = self.table_audit.rowCount()
                self.table_audit.insertRow(idx)
                timestamp = str(row[0] or "-")
                actor = str(row[1] or "-")
                action = str(row[2] or "-")
                target = str(row[3] or "-")

                self.table_audit.setItem(idx, 0, QTableWidgetItem(timestamp))
                self.table_audit.setItem(idx, 1, QTableWidgetItem(actor))
                
                action_item = QTableWidgetItem(action)
                if "Delete" in action:
                    action_item.setForeground(QColor(colors.DANGER))
                elif "Add" in action or "Create" in action:
                    action_item.setForeground(QColor(colors.SUCCESS))
                self.table_audit.setItem(idx, 2, action_item)
                self.table_audit.setItem(idx, 3, QTableWidgetItem(target))
        except Exception as e:
            print(f"Error loading logs: {e}")

    def export_audit_report_pdf(self):
        if not self.current_audit_report_rows:
            QMessageBox.warning(self, "Attention", "Aucune donnée à exporter dans le journal.")
            return

        pdf = FPDF(orientation='L')
        pdf.add_page()
        school_info = get_school_info_row()
        apply_grades_sheet_header(pdf, school_info, self.current_audit_report_title)

        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 7, f"Genere le: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        pdf.ln(2)

        headers = self.current_audit_report_headers
        col_widths = [48, 45, 88, 88]

        apply_table_header_style(pdf, "Arial", 9)
        for index, header in enumerate(headers):
            text = str(header).encode('latin-1', 'ignore').decode('latin-1')
            pdf.cell(col_widths[index], 8, text, 1, 0, 'C', True)
        pdf.ln()

        apply_table_body_style(pdf, "Arial", 8)
        for row_idx, row_values in enumerate(self.current_audit_report_rows):
            set_zebra_row_fill(pdf, row_idx)
            for col_idx, value in enumerate(row_values):
                text = str(value).encode('latin-1', 'ignore').decode('latin-1')
                align = 'L' if col_idx == 3 else 'C'
                pdf.cell(col_widths[col_idx], 7, text, 1, 0, align, True)
            pdf.ln()

        mode = get_report_output_mode("user_audit_report_mode", USER_AUDIT_REPORT_OUTPUT_MODE)
        output_pdf(
            pdf,
            self,
            default_name=f"Rapport_Audit_Utilisateurs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mode=mode,
            dialog_title="Exporter Rapport Journal d'Audit",
            success_save_message=f"Rapport du journal d'audit exporte ({self.current_audit_period_label}, max {len(self.current_audit_report_rows)} lignes).",
            success_print_message=f"Rapport du journal d'audit envoye a l'imprimante.",
        )

    def add_user(self):
        staff_id = self.combo_staff.currentData()
        username = self.txt_new_user.text().strip()
        email = self.txt_new_email.text().strip()
        password = self.txt_new_pass.text()
        role = self.combo_role.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Erreur", "Champs obligatoires manquants.")
            return
        
        try:
            is_valid, msg = security_utils.validate_password(password)
            if not is_valid:
                QMessageBox.warning(self, "Erreur", msg)
                return
                
            hashed_pwd = security_utils.hash_password(password)
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO Users (staff_id, username, email, password_hash, role, status)
                    VALUES (?, ?, ?, ?, ?, 'Actif')
                """, (staff_id, username, email, hashed_pwd, role))
                conn.commit()
            
            self.log_action("Add User", username)
            self.load_users()
            self.txt_new_user.clear()
            self.txt_new_email.clear()
            self.txt_new_pass.clear()
            QMessageBox.information(self, "Succès", "Utilisateur ajouté.")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Erreur", "Nom d'utilisateur déjà pris.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def select_user(self, item):
        row = item.row()
        self.selected_user_id = int(self.table.item(row, 0).text())
        self.selected_username = self.table.item(row, 2).text()
        staff_name = self.table.item(row, 1).text()
        
        colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
        self.lbl_selected_user.setText(f"👤 {self.selected_username} ({staff_name})")
        self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.PRIMARY}; padding: 8px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER};")

    def reset_password(self):
        if not self.selected_user_id:
            QMessageBox.warning(self, "Erreur", "Aucun utilisateur sélectionné.")
            return
        
        new_pwd = self.txt_reset_pass.text()
        if not new_pwd:
            QMessageBox.warning(self, "Erreur", "Entrez un nouveau mot de passe.")
            return

        is_valid, msg = security_utils.validate_password(new_pwd)
        if not is_valid:
            QMessageBox.warning(self, "Erreur", msg)
            return

        hashed_pwd = security_utils.hash_password(new_pwd)
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("UPDATE Users SET password_hash=? WHERE id=?", (hashed_pwd, self.selected_user_id))
                conn.commit()
            
            self.log_action("Reset Password", self.selected_username)
            self.txt_reset_pass.clear()
            QMessageBox.information(self, "Succès", "Mot de passe mis à jour.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_user(self):
        if not self.selected_user_id: return
        if self.selected_user_id == 1 or self.selected_username == 'admin':
            QMessageBox.warning(self, "Interdit", "Impossible de supprimer l'administrateur principal.")
            return

        if QMessageBox.question(self, "Confirmer", f"Supprimer '{self.selected_username}' ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    conn.execute("DELETE FROM Users WHERE id=?", (self.selected_user_id,))
                    conn.commit()
                
                self.log_action("Delete User", self.selected_username)
                self.load_users()
                self.lbl_selected_user.setText("Aucun utilisateur sélectionné")
                colors = ThemeManager.get_colors() if THEME_AVAILABLE else Colors()
                self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 8px; border-radius: 6px; border: 1px solid {colors.BORDER};")
                self.selected_user_id = None
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserManagementWindow()
    window.show()
    sys.exit(app.exec())