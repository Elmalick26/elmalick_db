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
    QWidget,
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
        self.setFixedSize(460, 620)
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
        colors = ThemeManager.get_colors()
        dark = ThemeManager.is_dark_mode()

        # ── خلفية متدرجة ───────────────────────────────────────
        grad_top = "#080D1A" if dark else "#0F1629"
        grad_bot = "#1A2744" if dark else "#1E3A5F"
        self.setStyleSheet(
            f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {grad_top}, stop:0.5 #162040, stop:1 {grad_bot});
                font-family: 'Segoe UI', 'Cairo', sans-serif;
            }}
        """
        )

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(36, 28, 36, 20)
        root.setSpacing(0)

        # ════════════════════════════════════════════════════
        #  البطاقة الرئيسية
        # ════════════════════════════════════════════════════
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card.setStyleSheet(
            f"""
            QFrame#LoginCard {{
                background-color: {colors.BG_CARD};
                border-radius: 20px;
                border: 1px solid {colors.BORDER};
            }}
        """
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 12)
        self.card.setGraphicsEffect(shadow)

        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # ── منطقة الشعار (Header Band) ──────────────────────
        header = QFrame()
        header.setFixedHeight(148)
        header.setStyleSheet(
            """
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4F46E5, stop:1 #7C3AED);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """
        )
        hdr_lay = QVBoxLayout(header)
        hdr_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_lay.setSpacing(6)

        lbl_logo = QLabel("🏫")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setFont(QFont("Segoe UI Emoji", 36))
        lbl_logo.setStyleSheet("background: transparent; color: white;")
        hdr_lay.addWidget(lbl_logo)

        lbl_app = QLabel("El Malick Gest")
        lbl_app.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_app.setStyleSheet(
            """
            color: white; font-size: 20px; font-weight: 800;
            letter-spacing: 0.5px; background: transparent;
        """
        )
        hdr_lay.addWidget(lbl_app)

        lbl_sub = QLabel("نظام إدارة المدارس — Système de Gestion Scolaire")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 11px; background: transparent;")
        hdr_lay.addWidget(lbl_sub)

        card_lay.addWidget(header)

        # ── منطقة النموذج (Form Area) ───────────────────────
        form_frame = QWidget()
        form_frame.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(36, 28, 36, 28)
        form_lay.setSpacing(14)

        # — عنوان النموذج —
        lbl_title = QLabel("Connexion / تسجيل الدخول")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet(
            f"""
            color: {colors.TEXT_PRIMARY}; font-size: 16px;
            font-weight: 700; background: transparent;
        """
        )
        form_lay.addWidget(lbl_title)
        form_lay.addSpacing(4)

        # — حقل اسم المستخدم —
        form_lay.addWidget(self._make_label("👤  Nom d'utilisateur / اسم المستخدم", colors))
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("admin")
        self.txt_user.setMinimumHeight(46)
        self._style_input(self.txt_user, colors)
        form_lay.addWidget(self.txt_user)

        # — حقل كلمة المرور —
        form_lay.addWidget(self._make_label("🔒  Mot de passe / كلمة المرور", colors))
        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("••••••••")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setMinimumHeight(46)
        self._style_input(self.txt_pass, colors)
        self.txt_pass.returnPressed.connect(self.check_login)

        # زر إظهار/إخفاء
        self._pass_visible = False
        self.btn_eye = QPushButton("👁")
        self.btn_eye.setFixedSize(46, 46)
        self.btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eye.setToolTip("إظهار / إخفاء كلمة المرور")
        self.btn_eye.setStyleSheet(
            f"""
            QPushButton {{
                background: {colors.INPUT_BG};
                border: 1.5px solid {colors.INPUT_BORDER};
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                font-size: 16px;
                color: {colors.TEXT_SECONDARY};
                font-family: "Segoe UI Emoji";
            }}
            QPushButton:hover {{ background: {colors.BORDER}; color: {colors.PRIMARY}; }}
        """
        )
        self.btn_eye.clicked.connect(self._toggle_password_visibility)
        # تعديل input ليفقد border-radius الجهة اليمنى
        self.txt_pass.setStyleSheet(
            self.txt_pass.styleSheet().replace(
                "border-radius: 8px",
                "border-radius: 8px; border-top-right-radius: 0px; border-bottom-right-radius: 0px;",
            )
        )
        pass_row.addWidget(self.txt_pass, 1)
        pass_row.addWidget(self.btn_eye)
        form_lay.addLayout(pass_row)

        # — رسالة الخطأ inline —
        self.lbl_error = QLabel("")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setFixedHeight(24)
        self.lbl_error.setStyleSheet(
            f"""
            color: {colors.DANGER}; font-size: 12px; font-weight: 600;
            background: transparent;
        """
        )
        self.lbl_error.hide()
        form_lay.addWidget(self.lbl_error)

        # — زر الدخول —
        form_lay.addSpacing(4)
        self.btn_login = QPushButton("  →  Connexion / تسجيل الدخول")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setMinimumHeight(50)
        self.btn_login.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4F46E5, stop:1 #7C3AED);
                color: white;
                font-weight: 700;
                font-size: 15px;
                border-radius: 10px;
                border: none;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4338CA, stop:1 #6D28D9);
            }}
            QPushButton:pressed {{
                background: #3730A3;
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: {colors.BORDER};
                color: {colors.TEXT_SECONDARY};
            }}
        """
        )
        self.btn_login.clicked.connect(self.check_login)
        form_lay.addWidget(self.btn_login)

        card_lay.addWidget(form_frame)
        root.addWidget(self.card)

        # ── Footer ───────────────────────────────────────────
        lbl_footer = QLabel("v2.0 Professional © 2026 — elmalickdiouf26@gmail.com")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 10px; margin-top: 12px;")
        root.addWidget(lbl_footer)

    # ── Helpers ──────────────────────────────────────────────
    def _make_label(self, text: str, colors) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600; background: transparent;"
        )
        return lbl

    def _style_input(self, widget: QLineEdit, colors):
        widget.setStyleSheet(
            f"""
            QLineEdit {{
                padding: 10px 14px;
                border: 1.5px solid {colors.INPUT_BORDER};
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

    def _toggle_password_visibility(self):
        self._pass_visible = not self._pass_visible
        if self._pass_visible:
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_eye.setText("🙈")
        else:
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_eye.setText("👁")

    def _show_error(self, msg: str):
        self.lbl_error.setText(f"⚠  {msg}")
        self.lbl_error.show()
        # اهتزاز خفيف للحقل
        self.txt_pass.setStyleSheet(
            self.txt_pass.styleSheet().replace("border: 1.5px solid", "border: 2px solid #DC2626; border:")
        )
        QTimer.singleShot(2500, self._clear_error)

    def _clear_error(self):
        self.lbl_error.hide()
        colors = ThemeManager.get_colors()
        self._style_input(self.txt_pass, colors)

    def apply_input_style(self, widget):
        """دالة تنسيق الحقول (للتوافق مع الكود القديم)"""
        colors = ThemeManager.get_colors()
        self._style_input(widget, colors)

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
            self._show_error("الرجاء ملء جميع الحقول — Veuillez remplir tous les champs")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("  ⏳  جاري التحقق...")

        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                repo = LoginRepository(conn)

                # 1. Vérification du verrouillage persistant (DB)
                _, is_locked = repo.get_lockout_status(user)
                if is_locked:
                    self._show_error("محاولات كثيرة — تم تعليق الحساب مؤقتاً")
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
                        self._show_error("هذا الحساب معطل — Ce compte est désactivé")
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
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("  →  Connexion / تسجيل الدخول")

        self._show_error("اسم المستخدم أو كلمة المرور غير صحيحة")
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
