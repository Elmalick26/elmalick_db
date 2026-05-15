import sys
import time
import os
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon
from database_setup import DatabaseManager
import security_utils
from app_logger import AppLogger
from ui_styles import Colors
from db_path import configure_qt_font_environment


def _resolve_app_icon_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "icon.ico"),
        os.path.join(base_dir, "assets", "icon.ico"),
        os.path.join(base_dir, "..", "icon.ico"),
        os.path.join(base_dir, "..", "assets", "icon.ico"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ""

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connexion / تسجيل الدخول")
        self.setFixedSize(500, 550)
        icon_path = _resolve_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.user_role = None
        self.failed_attempts = 0
        self.lockout_until = 0.0
        self.ensure_admin_exists() 
        self.init_ui()

    def ensure_admin_exists(self):
        try:
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
                    AppLogger.info("LoginWindow", "Compte administrateur par défaut créé (admin/admin)")
        except Exception as e:
            AppLogger.error("LoginWindow", f"Erreur lors de la vérification de l'administrateur: {str(e)}")

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
        # السماح بتسجيل الدخول عند الضغط على Enter في حقل كلمة المرور
        self.txt_pass.returnPressed.connect(self.check_login)
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
        lbl_footer = QLabel("v1.0 Professional Edition © 2026 Développé par El Malick\nجميع الحقوق محفوظة © 2026 التطوير بواسطة El Malick\nContact: elmalickdiouf26@gmail.com")
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
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text()

        if not user or not pwd:
            return

        if time.time() < self.lockout_until:
            msg = QMessageBox(self)
            msg.setWindowTitle("Erreur / خطأ")
            msg.setText("Trop de tentatives. Réessayez plus tard.\nمحاولات كثيرة. حاول لاحقاً")
            msg.setIcon(QMessageBox.Icon.Warning)
            colors = Colors()
            msg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")
            msg.exec()
            AppLogger.warning("LoginWindow", f"Tentative de connexion bloquée pour l'utilisateur '{user}' (Verrouillage actif)")
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, role, password_hash, status FROM Users WHERE username=?", (user,))
                result = cursor.fetchone()

            if result:
                user_id, role, stored_hash, status = result
                
                if status != "Actif":
                    QMessageBox.warning(self, "Erreur", "Ce compte est désactivé.\nهذا الحساب معطل.")
                    AppLogger.warning("LoginWindow", f"Tentative de connexion sur un compte désactivé '{user}'")
                    return

                if security_utils.verify_password(pwd, stored_hash):
                    self.user_role = role
                    self.failed_attempts = 0
                    self.lockout_until = 0.0

                    # تحذير أمني إذا كان الحساب الافتراضي لا يزال مستخدماً
                    if user == "admin" and pwd == "admin":
                        QMessageBox.warning(
                            self,
                            "Avertissement de sécurité",
                            "Le mot de passe par défaut est encore utilisé. Il est fortement recommandé de le modifier.\nيُنصح بتغيير كلمة المرور الافتراضية لحماية النظام."
                        )
                    
                    # تحديث التجزئة إذا كانت ضعيفة (Auto-upgrade legacy hashes)
                    if security_utils.needs_rehash(stored_hash):
                        new_hash = security_utils.hash_password(pwd)
                        with db.get_connection() as conn:
                            conn.execute("UPDATE Users SET password_hash=? WHERE id=?", (new_hash, user_id))
                            conn.commit()
                        AppLogger.info("LoginWindow", f"Mise à niveau du hachage du mot de passe pour '{user}'")
                    
                    AppLogger.info("LoginWindow", f"Connexion réussie pour l'utilisateur '{user}' (Rôle: {role})")
                    self.accept()
                    return

            # إذا وصل الكود هنا، فهذا يعني أن اسم المستخدم أو كلمة المرور غير صحيحة
            self.failed_attempts += 1
            AppLogger.warning("LoginWindow", f"Échec de connexion pour l'utilisateur '{user}' (Tentative {self.failed_attempts}/5)")
            
            if self.failed_attempts >= 5:
                self.lockout_until = time.time() + (5 * 60) # قفل لمدة 5 دقائق
                self.failed_attempts = 0
                AppLogger.warning("LoginWindow", f"Verrouillage déclenché après 5 échecs consécutifs.")

            msg = QMessageBox(self)
            msg.setWindowTitle("Erreur / خطأ")
            msg.setText("Nom d'utilisateur ou mot de passe incorrect.\nاسم المستخدم أو كلمة المرور غير صحيحة")
            msg.setIcon(QMessageBox.Icon.Warning)
            colors = Colors()
            msg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")
            msg.exec()
            
            # مسح حقل كلمة المرور فقط لمزيد من الأمان
            self.txt_pass.clear()
            
        except Exception as e:
            QMessageBox.critical(self, "Erreur Critique", f"Erreur de base de données: {str(e)}")
            AppLogger.error("LoginWindow", f"Erreur critique lors de la connexion: {str(e)}")

if __name__ == "__main__":
    configure_qt_font_environment()
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    login = LoginWindow()
    if login.exec():
        print(f"Logged in as: {login.user_role}")
    sys.exit()