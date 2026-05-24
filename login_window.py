import os
import sys

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

import security_utils
from app_logger import AppLogger
from database_setup import DatabaseManager, log_audit
from db_path import configure_qt_font_environment
from repositories.login_repo import LoginRepository
from ui_styles import Colors, ThemeManager
from validators import format_errors, validate_password_strength


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
        self.setFixedSize(520, 600)
        icon_path = _resolve_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.user_role = None
        self.ensure_admin_exists()
        ThemeManager.apply_theme(self)
        self.init_ui()
        self._start_fade_in()

    def _start_fade_in(self):
        """Fade-in animation when window opens — applied to card only, not whole window."""
        # دالة ناقلة: تُستدعى بعد بناء الواجهة لأن self.card يُنشأ في init_ui
        QTimer.singleShot(0, self._do_fade_in)

    def _do_fade_in(self):
        """تنفيذ الأنيميشن بعد اكتمال الواجهة."""
        if not hasattr(self, 'card'):
            return
        self._opacity_effect = QGraphicsOpacityEffect(self.card)
        # لا نطبّق على self مباشرة لتجنّب nested painters مع shadow الكارد
        self.card.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(lambda: self.card.setGraphicsEffect(None))
        self._anim.start()

    def ensure_admin_exists(self):
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = LoginRepository(conn)
                if repo.count_users() == 0:
                    default_pass = security_utils.hash_password("admin")
                    repo.insert_default_admin(default_pass)
                    conn.commit()
                    AppLogger.info("LoginWindow", "Compte administrateur par défaut créé (admin/admin)")
        except Exception as e:
            AppLogger.error("LoginWindow", f"Erreur lors de la vérification de l'administrateur: {str(e)}")

    def init_ui(self):
        # إعداد النمط العام — يستخدم ThemeManager تلقائياً (light أو dark)
        colors = ThemeManager.get_colors()
        dark = ThemeManager.is_dark_mode()
        # خلفية بتدرج لوني (gradient) تستجيب للثيم
        grad_top = "#0F172A" if dark else "#1E293B"
        grad_bot = "#1E3A5F" if dark else "#2D4A7A"
        self.setStyleSheet(
            f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {grad_top}, stop:1 {grad_bot});
                font-family: 'Segoe UI', 'Cairo', sans-serif;
            }}
        """
        )

        # التنسيق الرئيسي
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(50, 40, 50, 30)

        # إنشاء حاوية (Card)
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card.setStyleSheet(
            f"""
            QFrame#LoginCard {{
                background-color: {colors.BG_CARD};
                border-radius: 12px;
                border: 1px solid {colors.BORDER};
            }}
        """
        )

        # إضافة تأثير الظل — يُطبَّق دون opacity effect (لا nested painters)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        # تنسيق محتوى البطاقة
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(35, 35, 35, 35)
        card_layout.setSpacing(16)

        # 0. شعار التطبيق (Logo)
        lbl_logo = QLabel("🏫")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setFont(QFont("Segoe UI Emoji", 44))
        lbl_logo.setStyleSheet("background: transparent; margin-bottom: 4px;")
        card_layout.addWidget(lbl_logo)

        # 1. العنوان الرئيسي
        lbl_title = QLabel("El Malick Gest\nنظام إدارة المدارس")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(
            f"""
            QLabel {{
                color: {colors.TEXT_PRIMARY};
                font-size: 24px;
                font-weight: 800;
                margin-bottom: 15px;
            }}
        """
        )
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
        btn_login.setStyleSheet(
            f"""
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
        """
        )
        btn_login.clicked.connect(self.check_login)
        card_layout.addWidget(btn_login)

        # إضافة البطاقة للتنسيق الرئيسي
        main_layout.addWidget(self.card)

        # Footer
        lbl_footer = QLabel(
            "v1.0 Professional Edition © 2026 Développé par El Malick\nجميع الحقوق محفوظة © 2026 التطوير بواسطة El Malick\nContact: elmalickdiouf26@gmail.com"
        )
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer.setStyleSheet(f"color: {colors.TEXT_SECONDARY}; font-size: 11px; margin-top: 15px;")
        main_layout.addWidget(lbl_footer)

    def apply_input_style(self, widget):
        """دالة تنسيق الحقول بنمط Slate"""
        colors = ThemeManager.get_colors()
        widget.setStyleSheet(
            f"""
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
        """
        )

    def _force_change_default_password(self, conn, user_id: int) -> bool:
        """
        فرض تغيير كلمة المرور الافتراضية admin/admin.
        العائد: True إذا نجح التغيير، False إذا ألغى المستخدم أو فشل.
        """
        dlg = QMessageBox(self)
        dlg.setWindowTitle("🔐 تغيير كلمة المرور الإجبارية / Changement de mot de passe obligatoire")
        dlg.setText(
            "أنت تستخدم كلمة المرور الافتراضية (admin/admin).\n"
            "يجب تغييرها الآن لحماية النظام.\n\n"
            "Vous utilisez le mot de passe par défaut (admin/admin).\n"
            "Il doit être changé maintenant pour sécuriser le système."
        )
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        colors = ThemeManager.get_colors()
        dlg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")

        if dlg.exec() != QMessageBox.StandardButton.Ok:
            AppLogger.warning("LoginWindow", "المستخدم ألغى تغيير كلمة المرور الافتراضية")
            return False

        # حوار إدخال كلمة المرور الجديدة
        while True:
            new_pass, ok = QInputDialog.getText(
                self,
                "كلمة المرور الجديدة / Nouveau mot de passe",
                "أدخل كلمة مرور قوية (8+ أحرف، أرقام، حروف):\nEntrez un mot de passe fort (8+ caractères, chiffres, lettres):",
                QLineEdit.EchoMode.Password,
            )

            if not ok:
                AppLogger.warning("LoginWindow", "المستخدم ألغى دخول كلمة المرور الجديدة")
                return False

            # التحقق من قوة كلمة المرور
            errors = validate_password_strength(new_pass)
            if errors:
                QMessageBox.warning(self, "كلمة مرور ضعيفة / Mot de passe faible", format_errors(errors))
                continue

            # تأكيد كلمة المرور
            confirm_pass, ok = QInputDialog.getText(
                self,
                "تأكيد كلمة المرور / Confirmer le mot de passe",
                "أعد إدخال كلمة المرور:\nVérifiez le mot de passe:",
                QLineEdit.EchoMode.Password,
            )

            if not ok:
                AppLogger.warning("LoginWindow", "المستخدم ألغى تأكيد كلمة المرور")
                return False

            if new_pass != confirm_pass:
                QMessageBox.warning(
                    self,
                    "عدم التطابق / Non-correspondance",
                    "كلمتا المرور غير متطابقتين.\nLes mots de passe ne correspondent pas.",
                )
                continue

            # حفظ كلمة المرور الجديدة
            try:
                new_hash = security_utils.hash_password(new_pass)
                LoginRepository(conn).update_password_hash(user_id, new_hash)
                conn.commit()

                log_audit(conn, "admin", "FORCE_PASSWORD_CHANGE", "admin")

                AppLogger.info("LoginWindow", "تم تغيير كلمة مرور المسؤول الافتراضية بنجاح")
                QMessageBox.information(
                    self, "تم / Succès", "تم تغيير كلمة المرور بنجاح!\nMot de passe changé avec succès!"
                )
                return True
            except Exception as e:
                AppLogger.error("LoginWindow", f"فشل تحديث كلمة مرور المسؤول: {e}")
                QMessageBox.critical(self, "خطأ / Erreur", f"فشل حفظ كلمة المرور: {e}\nÉchec de l'enregistrement: {e}")
                return False

    def check_login(self):
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text()

        if not user or not pwd:
            return

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = LoginRepository(conn)

                # 1. Vérification du verrouillage persistant (DB)
                _, is_locked = repo.get_lockout_status(user)
                if is_locked:
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Erreur / خطأ")
                    msg.setText("Trop de tentatives. Réessayez plus tard.\nمحاولات كثيرة. حاول لاحقاً")
                    msg.setIcon(QMessageBox.Icon.Warning)
                    colors = ThemeManager.get_colors()
                    msg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")
                    msg.exec()
                    AppLogger.warning(
                        "LoginWindow",
                        f"Tentative de connexion bloquée pour l'utilisateur '{user}' (Verrouillage actif)",
                    )
                    return

                result = repo.get_user_for_login(user)
                if result:
                    user_id, role, stored_hash, status = result

                    if status != "Actif":
                        log_audit(conn, user, "LOGIN_DISABLED", user)
                        QMessageBox.warning(self, "Erreur", "Ce compte est désactivé.\nهذا الحساب معطل.")
                        AppLogger.warning("LoginWindow", f"Tentative de connexion sur un compte désactivé '{user}'")
                        return

                    if security_utils.verify_password(pwd, stored_hash):
                        self.user_role = role
                        repo.clear_attempts(user)

                        log_audit(conn, user, "LOGIN", user)

                        # فرض تغيير كلمة المرور الافتراضية — الحساب الافتراضي admin/admin
                        if (
                            user == "admin"
                            and pwd == "admin"
                            and not self._force_change_default_password(conn, user_id)
                        ):
                            return

                        # تحديث التجزئة إذا كانت ضعيفة (Auto-upgrade legacy hashes)
                        if security_utils.needs_rehash(stored_hash):
                            new_hash = security_utils.hash_password(pwd)
                            LoginRepository(conn).update_password_hash(user_id, new_hash)
                            conn.commit()
                            AppLogger.info("LoginWindow", f"Mise à niveau du hachage du mot de passe pour '{user}'")

                        AppLogger.info("LoginWindow", f"Connexion réussie pour l'utilisateur '{user}' (Rôle: {role})")
                        self.accept()
                        return

                # Échec d'authentification — enregistrement et verrouillage éventuel
                log_audit(conn, user, "LOGIN_FAILED", user)
                now_locked = repo.record_failed_attempt(user)
                if now_locked:
                    AppLogger.warning("LoginWindow", "Verrouillage déclenché après 5 échecs consécutifs.")
                else:
                    AppLogger.warning("LoginWindow", f"Échec de connexion pour l'utilisateur '{user}'")

        except Exception as e:
            QMessageBox.critical(self, "Erreur Critique", f"Erreur de base de données: {str(e)}")
            AppLogger.error("LoginWindow", f"Erreur critique lors de la connexion: {str(e)}")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Erreur / خطأ")
        msg.setText("Nom d'utilisateur ou mot de passe incorrect.\nاسم المستخدم أو كلمة المرور غير صحيحة")
        msg.setIcon(QMessageBox.Icon.Warning)
        colors = ThemeManager.get_colors()
        msg.setStyleSheet(f"background-color: {colors.BG_CARD}; color: {colors.TEXT_PRIMARY};")
        msg.exec()

        # مسح حقل كلمة المرور فقط لمزيد من الأمان
        self.txt_pass.clear()


if __name__ == "__main__":
    configure_qt_font_environment()
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    login = LoginWindow()
    if login.exec():
        AppLogger.info("LoginWindow", f"Logged in as: {login.user_role}")
    sys.exit()
