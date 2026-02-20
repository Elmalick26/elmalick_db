import sys
import time
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database_setup import DatabaseManager
import security_utils

from ui_styles import Colors

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connexion / تسجيل الدخول")
        self.setFixedSize(500, 550)
        self.user_role = None
        self.failed_attempts = 0
        self.lockout_until = 0.0
        self.ensure_admin_exists() 
        self.init_ui()

    def ensure_admin_exists(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM Users")
            if cursor.fetchone()[0] == 0:
                default_pass = security_utils.hash_password("admin")
                cursor.execute("""
                    INSERT INTO Users (username, email, password_hash, role, status) 
                    VALUES (?, ?, ?, ?, ?)
                """, ("admin", "admin@school.local", default_pass, "Admin", "Actif"))
                conn.commit()

    def init_ui(self):
        # إعداد النمط العام - Deep Slate Theme
        colors = Colors()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors.BG_MAIN};
                font-family: 'Segoe UI', 'Cairo', sans-serif;
            }}
        """)
        
        # التنسيق الرئيسي
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(50, 50, 50, 50)

        # إنشاء حاوية (Card)
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card.setStyleSheet(f"""
            QFrame#LoginCard {{
                background-color: {colors.BG_CARD};
                border-radius: 12px;
                border: 1px solid {colors.BORDER};
            }}
        """)
        
        # إضافة تأثير الظل
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(15, 23, 42, 30)) # لون ظل داكن (Slate Dark)
        shadow.setOffset(0, 5)
        self.card.setGraphicsEffect(shadow)

        # تنسيق محتوى البطاقة
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(35, 45, 35, 45)
        card_layout.setSpacing(18)

        # 1. العنوان الرئيسي
        lbl_title = QLabel("Système Scolaire\nنظام إدارة المدارس")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(f"""
            QLabel {{
                color: {colors.TEXT_PRIMARY};
                font-size: 24px;
                font-weight: 800;
                margin-bottom: 15px;
            }}
        """)
        card_layout.addWidget(lbl_title)

        # 2. حقل اسم المستخدم
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Nom d'utilisateur / اسم المستخدم")
        self.txt_user.setMinimumHeight(48)
        self.apply_input_style(self.txt_user)
        card_layout.addWidget(self.txt_user)

        # 3. حقل كلمة المرور
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Mot de passe / كلمة المرور")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setMinimumHeight(48)
        self.apply_input_style(self.txt_pass)
        card_layout.addWidget(self.txt_pass)

        # مسافة إضافية
        card_layout.addSpacing(15)

        # 4. زر الدخول (Deep Slate Style)
        btn_login = QPushButton("Connexion / تسجيل الدخول")
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setMinimumHeight(52)
        btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.PRIMARY};
                color: white; 
                font-weight: bold; 
                font-size: 16px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ 
                background-color: {colors.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {colors.PRIMARY_DARK};
                padding-top: 2px;
            }}
        """)
        btn_login.clicked.connect(self.check_login)
        card_layout.addWidget(btn_login)

        # إضافة البطاقة للتنسيق الرئيسي
        main_layout.addWidget(self.card)

        # Footer
        lbl_footer = QLabel("v1.0 Professional Edition © 2026\nDevelopé par El Malick")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 11px; margin-top: 15px;")
        main_layout.addWidget(lbl_footer)

    def apply_input_style(self, widget):
        """دالة تنسيق الحقول بنمط Slate"""
        colors = Colors()
        widget.setStyleSheet(f"""
            QLineEdit {{
                padding: 10px 15px;
                border: 1px solid {colors.BORDER};
                border-radius: 8px;
                background-color: {colors.INPUT_BG};
                color: {colors.TEXT_PRIMARY};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid {colors.BORDER_FOCUS};
                background-color: {colors.INPUT_BG_FOCUS};
            }}
        """)

    def check_login(self):
        user = self.txt_user.text()
        pwd = self.txt_pass.text()

        if time.time() < self.lockout_until:
            msg = QMessageBox(self)
            msg.setWindowTitle("Erreur / خطأ")
            msg.setText("Trop de tentatives. Réessayez plus tard.\nمحاولات كثيرة. حاول لاحقا")
            msg.setIcon(QMessageBox.Icon.Warning)
            colors = Colors()
            msg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")
            msg.exec()
            return

        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Fetch hash to verify in Python (for bcrypt support)
            cursor.execute("SELECT id, role, password_hash FROM Users WHERE username=?", (user,))
            result = cursor.fetchone()

        if result:
            user_id, role, stored_hash = result
            if security_utils.verify_password(pwd, stored_hash):
                self.user_role = role
                self.failed_attempts = 0
                self.lockout_until = 0.0

                if user == "admin" and pwd == "admin":
                    QMessageBox.warning(
                        self,
                        "Avertissement",
                        "Le mot de passe par defaut est encore utilise. Modifiez-le depuis la gestion des utilisateurs."
                    )
                
                # Auto-upgrade legacy hashes to bcrypt
                if security_utils.needs_rehash(stored_hash):
                    new_hash = security_utils.hash_password(pwd)
                    with db.get_connection() as conn:
                        conn.execute("UPDATE Users SET password_hash=? WHERE id=?", (new_hash, user_id))
                        conn.commit()
                    print(f"DEBUG: Upgraded password for user {user} to bcrypt.")
                
                self.accept()
                return

        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.lockout_until = time.time() + (5 * 60)
            self.failed_attempts = 0

        msg = QMessageBox(self)
        msg.setWindowTitle("Erreur / خطأ")
        msg.setText("Nom d'utilisateur ou mot de passe incorrect.\nاسم المستخدم أو كلمة المرور غير صحيحة")
        msg.setIcon(QMessageBox.Icon.Warning)
        colors = Colors()
        msg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")
        msg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    login = LoginWindow()
    if login.exec():
        print(f"Logged in as: {login.user_role}")
    sys.exit()