import sys
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QMessageBox, QHeaderView, QGroupBox, QFrame, 
                             QTabWidget, QGridLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database_setup import DatabaseManager
import security_utils

from ui_styles import ThemeManager, Colors, get_card_style, apply_shadow_to_widget, get_table_style, get_tabs_style

THEME_AVAILABLE = True


class UserManagementWindow(QMainWindow):
    def __init__(self, current_user="Admin"):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Gestion des Utilisateurs / إدارة المستخدمين")
        self.setMinimumSize(1100, 700)

        # تطبيق المظهر (Dark Mode أو Light Mode)
        if THEME_AVAILABLE:
            ThemeManager.apply_theme(self)
        else:
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

        self.selected_user_id = None
        self.selected_username = ""

        self.ensure_admin_exists()
        self.init_ui()
        self.load_users()
        self.load_audit_logs()

    def ensure_admin_exists(self):
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

    def log_action(self, action, target):
        """Helper to log actions to DB"""
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

        # 1. Header Frame
        header_frame = QFrame()
        if THEME_AVAILABLE:
            bg_header = ThemeManager.get_colors().BG_HEADER
        else:
            bg_header = Colors().BG_HEADER
            
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
        
        icon_lbl = QLabel("🔐")
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        
        title_layout = QVBoxLayout()
        header_lbl = QLabel("GESTION DES UTILISATEURS")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        if THEME_AVAILABLE:
            header_lbl.setStyleSheet(f"color: {ThemeManager.get_colors().HEADER_TEXT}; background: transparent;")
        else:
            header_lbl.setStyleSheet(f"color: {Colors().HEADER_TEXT}; background: transparent;")
        
        sub_lbl = QLabel("إدارة الصلاحيات، الحسابات، وسجل العمليات")
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

    def styled_input(self, placeholder):
        le = QLineEdit()
        le.setPlaceholderText(placeholder)
        le.setMinimumHeight(38)
        return le

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

    def setup_users_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 1. Top Section: Add User & Manage User
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Left Card: Add User
        add_card = self.create_card()
        alay = QVBoxLayout(add_card)
        alay.setContentsMargins(15, 15, 15, 15)
        
        lbl_add_title = QLabel("➕ Nouveau Utilisateur / إضافة مستخدم")
        if THEME_AVAILABLE:
            lbl_add_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        else:
            lbl_add_title.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
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
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_add.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_add.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.SUCCESS}; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.SUCCESS_HOVER}; }}
            """)
        btn_add.clicked.connect(self.add_user)
        
        alay.addLayout(form_grid)
        alay.addWidget(btn_add)
        alay.addStretch()
        
        top_layout.addWidget(add_card, 1) # Weight 1

        # Right Card: Manage Selected User
        manage_card = self.create_card()
        mlay = QVBoxLayout(manage_card)
        mlay.setContentsMargins(15, 15, 15, 15)
        
        lbl_manage_title = QLabel("🔧 Gestion & Sécurité / إدارة الحساب")
        if THEME_AVAILABLE:
            lbl_manage_title.setStyleSheet(f"font-weight: bold; color: {ThemeManager.get_colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        else:
            lbl_manage_title.setStyleSheet(f"font-weight: bold; color: {Colors().TEXT_PRIMARY}; font-size: 14px; margin-bottom: 5px;")
        mlay.addWidget(lbl_manage_title)
        
        self.lbl_selected_user = QLabel("Aucun utilisateur sélectionné")
        self.lbl_selected_user.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 8px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER};")
        else:
            colors = Colors()
            self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 8px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER};")
        mlay.addWidget(self.lbl_selected_user)
        
        mlay.addSpacing(10)
        mlay.addWidget(QLabel("Réinitialiser le mot de passe:"))
        self.txt_reset_pass = self.styled_input("Nouveau mot de passe")
        self.txt_reset_pass.setEchoMode(QLineEdit.EchoMode.Password)
        mlay.addWidget(self.txt_reset_pass)
        
        btn_reset = QPushButton("Modifier le Mot de Passe")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_reset.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_reset.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.PRIMARY}; color: white; font-weight: bold; padding: 8px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.PRIMARY_HOVER}; }}
            """)
        btn_reset.clicked.connect(self.reset_password)
        mlay.addWidget(btn_reset)
        
        mlay.addSpacing(15)
        btn_delete = QPushButton("Supprimer ce Compte")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            btn_delete.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; padding: 8px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        else:
            colors = Colors()
            btn_delete.setStyleSheet(f"""
                QPushButton {{ background-color: {colors.DANGER}; color: white; font-weight: bold; padding: 8px; border-radius: 6px; border: none; }}
                QPushButton:hover {{ background-color: {colors.DANGER_HOVER}; }}
            """)
        btn_delete.clicked.connect(self.delete_user)
        mlay.addWidget(btn_delete)
        mlay.addStretch()
        
        top_layout.addWidget(manage_card, 1) # Weight 1
        
        layout.addLayout(top_layout)

        # 2. Bottom Section: Users Table
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
        
        # Filter Card
        filter_card = self.create_card()
        flay = QHBoxLayout(filter_card)
        flay.setContentsMargins(10, 10, 10, 10)
        
        self.txt_audit_search = self.styled_input("🔍 Rechercher dans l'historique (Nom, Action, Date)...")
        self.txt_audit_search.textChanged.connect(self.load_audit_logs)
        flay.addWidget(self.txt_audit_search)
        
        layout.addWidget(filter_card)

        # Audit Table
        self.table_audit = QTableWidget()
        self.style_table(self.table_audit)
        self.table_audit.setColumnCount(4)
        self.table_audit.setHorizontalHeaderLabels(["Date/Heure", "Acteur (من)", "Action (ماذا)", "Cible (على من)"])
        self.table_audit.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table_audit)
        
        self.tabs.addTab(tab, "  📜 Journal d'Audit / السجل  ")

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
                display_name = f"{first_name} {last_name}"
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
                self.table.setItem(idx, 1, QTableWidgetItem(staff_name))
                self.table.setItem(idx, 2, QTableWidgetItem(username))
                self.table.setItem(idx, 3, QTableWidgetItem(email))
                self.table.setItem(idx, 4, QTableWidgetItem(role))
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur: {e}")

    def load_audit_logs(self):
        self.table_audit.setRowCount(0)
        search = self.txt_audit_search.text()
        db = DatabaseManager()
        
        query = "SELECT timestamp, actor, action, target FROM AuditLogs WHERE actor LIKE ? OR action LIKE ? OR target LIKE ? ORDER BY id DESC LIMIT 100"
        params = (f"%{search}%", f"%{search}%", f"%{search}%")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for row in rows:
            idx = self.table_audit.rowCount()
            self.table_audit.insertRow(idx)
            self.table_audit.setItem(idx, 0, QTableWidgetItem(row[0]))
            self.table_audit.setItem(idx, 1, QTableWidgetItem(row[1]))
            
            action_item = QTableWidgetItem(row[2])
            if "Delete" in row[2]:
                if THEME_AVAILABLE:
                    action_item.setForeground(QColor(ThemeManager.get_colors().DANGER))
                else:
                    action_item.setForeground(QColor(Colors().DANGER))
            elif "Add" in row[2]:
                if THEME_AVAILABLE:
                    action_item.setForeground(QColor(ThemeManager.get_colors().SUCCESS))
                else:
                    action_item.setForeground(QColor(Colors().SUCCESS))
            self.table_audit.setItem(idx, 2, action_item)
            
            self.table_audit.setItem(idx, 3, QTableWidgetItem(row[3]))

    def add_user(self):
        staff_id = self.combo_staff.currentData()
        username = self.txt_new_user.text()
        email = self.txt_new_email.text()
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
        
        self.lbl_selected_user.setText(f"👤 {self.selected_username} ({staff_name})")
        if THEME_AVAILABLE:
            colors = ThemeManager.get_colors()
            self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.PRIMARY}; padding: 8px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER};")
        else:
            colors = Colors()
            self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.PRIMARY_DARK}; padding: 8px; border-radius: 6px; font-weight: bold; border: 1px solid {colors.BORDER};")

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
            db = DatabaseManager()
            with db.get_connection() as conn:
                conn.execute("DELETE FROM Users WHERE id=?", (self.selected_user_id,))
                conn.commit()
            
            self.log_action("Delete User", self.selected_username)
            self.load_users()
            self.lbl_selected_user.setText("Aucun utilisateur sélectionné")
            if THEME_AVAILABLE:
                colors = ThemeManager.get_colors()
                self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 8px; border-radius: 6px; border: 1px solid {colors.BORDER};")
            else:
                colors = Colors()
                self.lbl_selected_user.setStyleSheet(f"background-color: {colors.BG_MAIN}; color: {colors.TEXT_SECONDARY}; padding: 8px; border-radius: 6px; border: 1px solid {colors.BORDER};")
            self.selected_user_id = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserManagementWindow()
    window.show()
    sys.exit(app.exec())