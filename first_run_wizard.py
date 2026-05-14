"""
first_run_wizard.py — معالج الإعداد الأول
First-Run Setup Wizard for El Malick Gest

يظهر هذا المعالج عند:
- أول تشغيل للبرنامج
- عندما تكون كلمة مرور قاعدة البيانات غير مضبوطة
- عندما يكون اسم المدرسة لا يزال افتراضياً

الاستخدام من main_dashbord.py:
    from first_run_wizard import should_run_wizard, FirstRunWizard
    if should_run_wizard():
        wizard = FirstRunWizard()
        if wizard.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)  # لا يمكن تشغيل البرنامج بدون إعداد
"""

import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QStackedWidget, QWidget, QFileDialog, QMessageBox,
    QFormLayout, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from config_manager import ConfigManager
from app_logger import AppLogger

# ─────────────────────────────────────────────────────────────────────────────
# دالة الفحص: هل يجب تشغيل المعالج؟
# ─────────────────────────────────────────────────────────────────────────────

def should_run_wizard() -> bool:
    """
    تعيد True إذا كان المعالج يجب أن يعمل.
    الشروط:
      - كلمة مرور DB غير مضبوطة في keyring ولا في config.ini
      - أو اسم المدرسة لم يُغيَّر من القيمة الافتراضية
    """
    config = ConfigManager()

    # فحص كلمة مرور DB
    password = config.db_password
    placeholders = ('your_password_here', '', 'None', 'null', None)
    if password in placeholders:
        return True

    # فحص اسم المدرسة
    school_name = config.school_name
    if not school_name or school_name == "El Malick School Management System":
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# المعالج الرئيسي
# ─────────────────────────────────────────────────────────────────────────────

class FirstRunWizard(QDialog):
    """معالج الإعداد الأول — QDialog متعدد الخطوات"""

    TOTAL_STEPS = 5  # الترحيب، معلومات المدرسة، قاعدة البيانات، المسؤول، ملخص

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إعداد البرنامج / Configuration initiale — El Malick Gest")
        self.setMinimumSize(600, 500)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.config = ConfigManager()
        self._build_ui()

    # ──────────────────────────────── بناء الواجهة ────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # شريط التقدم العلوي
        self.progress_bar = self._make_progress_bar()
        root.addWidget(self.progress_bar)

        # المحتوى المتعدد الخطوات
        self.stack = QStackedWidget()
        self.stack.addWidget(self._step_welcome())       # 0
        self.stack.addWidget(self._step_school_info())   # 1
        self.stack.addWidget(self._step_database())      # 2
        self.stack.addWidget(self._step_admin())         # 3
        self.stack.addWidget(self._step_summary())       # 4
        root.addWidget(self.stack, 1)

        # أزرار التنقل
        nav = self._make_nav_buttons()
        root.addWidget(nav)

        self._update_nav()

    def _make_progress_bar(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(6)
        frame.setStyleSheet("background-color: #e0e0e0;")
        self._progress_indicator = QFrame(frame)
        self._progress_indicator.setStyleSheet("background-color: #1976D2; border-radius: 3px;")
        self._progress_indicator.setFixedHeight(6)
        self._update_progress_bar()
        return frame

    def _update_progress_bar(self):
        if hasattr(self, 'progress_bar'):
            step = self.stack.currentIndex() if hasattr(self, 'stack') else 0
            width = self.progress_bar.width() if self.progress_bar.width() > 0 else 600
            ratio = (step + 1) / self.TOTAL_STEPS
            self._progress_indicator.setFixedWidth(int(width * ratio))

    def _make_nav_buttons(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background-color: #f5f5f5; border-top: 1px solid #e0e0e0;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(20, 12, 20, 12)

        self.btn_back = QPushButton("◄ رجوع / Retour")
        self.btn_back.setFixedWidth(160)
        self.btn_back.setStyleSheet(
            "padding: 8px; border-radius: 6px; background-color: #eeeeee; color: #333; border: 1px solid #ccc;"
        )
        self.btn_back.clicked.connect(self._go_back)

        self.btn_next = QPushButton("التالي / Suivant ►")
        self.btn_next.setFixedWidth(160)
        self.btn_next.setStyleSheet(
            "padding: 8px; border-radius: 6px; background-color: #1976D2; color: white; font-weight: bold;"
        )
        self.btn_next.clicked.connect(self._go_next)

        layout.addWidget(self.btn_back)
        layout.addStretch()
        layout.addWidget(self.btn_next)
        return w

    # ──────────────────────────── الخطوة 0: الترحيب ──────────────────────────

    def _step_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(60, 40, 60, 40)

        icon_lbl = QLabel("🏫")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("مرحباً بك في El Malick Gest")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #1976D2;")

        subtitle = QLabel("Bienvenue dans El Malick Gest")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #555;")

        desc = QLabel(
            "سيساعدك هذا المعالج على إعداد البرنامج في دقائق.\n"
            "يرجى الإجابة على الأسئلة التالية للبدء.\n\n"
            "Cet assistant vous guidera pour configurer le logiciel en quelques minutes."
        )
        desc.setFont(QFont("Segoe UI", 11))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #444; line-height: 1.6;")

        for widget in (icon_lbl, title, subtitle, desc):
            layout.addWidget(widget)

        return w

    # ─────────────────────── الخطوة 1: معلومات المدرسة ───────────────────────

    def _step_school_info(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(16)

        title = QLabel("🏫  معلومات المدرسة / Informations de l'école")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.txt_school_name = QLineEdit()
        self.txt_school_name.setPlaceholderText("مثال: مدرسة النور الابتدائية / École Primaire El Nour")
        self.txt_school_name.setText(
            self.config.school_name
            if self.config.school_name != "El Malick School Management System"
            else ""
        )
        self.txt_school_name.setMinimumHeight(36)

        self.txt_school_location = QLineEdit()
        self.txt_school_location.setPlaceholderText("مثال: داكار، السنغال / Dakar, Sénégal")
        self.txt_school_location.setText(self.config.get("APPLICATION", "school_location", ""))
        self.txt_school_location.setMinimumHeight(36)

        self.txt_school_phone = QLineEdit()
        self.txt_school_phone.setPlaceholderText("+221 XX XXX XXXX")
        self.txt_school_phone.setMinimumHeight(36)

        self.txt_backup_path = QLineEdit()
        self.txt_backup_path.setPlaceholderText("مسار مجلد النسخ الاحتياطي")
        self.txt_backup_path.setText(self.config.backup_dir)
        self.txt_backup_path.setMinimumHeight(36)
        self.txt_backup_path.setReadOnly(True)

        btn_browse = QPushButton("📂 تصفّح")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse_backup_dir)

        backup_row = QHBoxLayout()
        backup_row.addWidget(self.txt_backup_path)
        backup_row.addWidget(btn_browse)
        backup_widget = QWidget()
        backup_widget.setLayout(backup_row)

        form.addRow("اسم المدرسة *:", self.txt_school_name)
        form.addRow("الموقع / Ville:", self.txt_school_location)
        form.addRow("الهاتف / Téléphone:", self.txt_school_phone)
        form.addRow("مجلد النسخ الاحتياطي:", backup_widget)

        layout.addLayout(form)
        layout.addStretch()
        return w

    def _browse_backup_dir(self):
        path = QFileDialog.getExistingDirectory(self, "اختر مجلد النسخ الاحتياطي")
        if path:
            self.txt_backup_path.setText(path)

    # ────────────────────────── الخطوة 2: قاعدة البيانات ─────────────────────

    def _step_database(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(16)

        title = QLabel("🗄️  اتصال قاعدة البيانات / Connexion PostgreSQL")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.txt_db_host = QLineEdit(self.config.db_host)
        self.txt_db_host.setMinimumHeight(36)

        self.spin_db_port = QSpinBox()
        self.spin_db_port.setRange(1, 65535)
        self.spin_db_port.setValue(self.config.db_port)
        self.spin_db_port.setMinimumHeight(36)

        self.txt_db_name = QLineEdit(self.config.db_name)
        self.txt_db_name.setMinimumHeight(36)

        self.txt_db_user = QLineEdit(self.config.db_user)
        self.txt_db_user.setMinimumHeight(36)

        self.txt_db_pass = QLineEdit()
        self.txt_db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_db_pass.setPlaceholderText("كلمة مرور PostgreSQL")
        self.txt_db_pass.setMinimumHeight(36)
        # لا نُعبّئ كلمة المرور مسبقاً لأسباب أمنية

        form.addRow("المضيف / Hôte:", self.txt_db_host)
        form.addRow("المنفذ / Port:", self.spin_db_port)
        form.addRow("اسم قاعدة البيانات:", self.txt_db_name)
        form.addRow("اسم المستخدم:", self.txt_db_user)
        form.addRow("كلمة المرور *:", self.txt_db_pass)

        layout.addLayout(form)

        # زر اختبار الاتصال
        btn_test = QPushButton("🔌 اختبار الاتصال / Tester la connexion")
        btn_test.setStyleSheet(
            "padding: 8px 16px; background-color: #43A047; color: white; "
            "border-radius: 6px; font-weight: bold;"
        )
        btn_test.clicked.connect(self._test_db_connection)
        layout.addWidget(btn_test, 0, Qt.AlignmentFlag.AlignLeft)

        self.lbl_conn_status = QLabel("")
        self.lbl_conn_status.setWordWrap(True)
        layout.addWidget(self.lbl_conn_status)

        layout.addStretch()
        return w

    def _test_db_connection(self):
        """اختبار الاتصال بقاعدة البيانات بالقيم المدخلة"""
        self.lbl_conn_status.setText("⏳ جار الاختبار...")
        self.lbl_conn_status.setStyleSheet("color: #888;")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.txt_db_host.text().strip(),
                port=self.spin_db_port.value(),
                dbname=self.txt_db_name.text().strip(),
                user=self.txt_db_user.text().strip(),
                password=self.txt_db_pass.text(),
                connect_timeout=5
            )
            conn.close()
            self.lbl_conn_status.setText("✅ الاتصال ناجح! / Connexion réussie!")
            self.lbl_conn_status.setStyleSheet("color: #2E7D32; font-weight: bold;")
        except Exception as e:
            self.lbl_conn_status.setText(f"❌ فشل الاتصال: {e}")
            self.lbl_conn_status.setStyleSheet("color: #C62828; font-weight: bold;")

    # ─────────────────────────── الخطوة 3: حساب المسؤول ─────────────────────

    def _step_admin(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(16)

        title = QLabel("🔐  حساب المسؤول / Compte Administrateur")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        layout.addWidget(title)

        note = QLabel(
            "ستُستخدم هذه البيانات لتسجيل الدخول إلى النظام.\n"
            "Ces informations seront utilisées pour se connecter au système."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.txt_admin_user = QLineEdit("admin")
        self.txt_admin_user.setMinimumHeight(36)

        self.txt_admin_pass = QLineEdit()
        self.txt_admin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_admin_pass.setPlaceholderText("8 أحرف على الأقل، يحتوي أرقاماً وحروف")
        self.txt_admin_pass.setMinimumHeight(36)
        self.txt_admin_pass.textChanged.connect(self._update_password_strength)

        self.txt_admin_confirm = QLineEdit()
        self.txt_admin_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_admin_confirm.setPlaceholderText("تأكيد كلمة المرور / Confirmer")
        self.txt_admin_confirm.setMinimumHeight(36)

        self.lbl_pass_strength = QLabel("")
        self.lbl_pass_strength.setWordWrap(True)

        form.addRow("اسم المستخدم:", self.txt_admin_user)
        form.addRow("كلمة المرور *:", self.txt_admin_pass)
        form.addRow("تأكيد كلمة المرور *:", self.txt_admin_confirm)
        form.addRow("", self.lbl_pass_strength)

        layout.addLayout(form)
        layout.addStretch()
        return w

    def _update_password_strength(self):
        from validators import validate_password_strength
        pwd = self.txt_admin_pass.text()
        errors = validate_password_strength(pwd)
        if not pwd:
            self.lbl_pass_strength.setText("")
        elif errors:
            self.lbl_pass_strength.setText("⚠️ " + " | ".join(errors))
            self.lbl_pass_strength.setStyleSheet("color: #E65100;")
        else:
            self.lbl_pass_strength.setText("✅ كلمة مرور قوية / Mot de passe fort")
            self.lbl_pass_strength.setStyleSheet("color: #2E7D32; font-weight: bold;")

    # ──────────────────────────── الخطوة 4: الملخص ───────────────────────────

    def _step_summary(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(16)

        title = QLabel("✅  الملخص / Récapitulatif")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #1976D2; margin-bottom: 8px;")
        layout.addWidget(title)

        self.lbl_summary = QLabel("انقر 'التالي' لتأكيد الإعدادات وحفظها.")
        self.lbl_summary.setWordWrap(True)
        self.lbl_summary.setStyleSheet("color: #333; font-size: 12px; line-height: 1.8;")
        layout.addWidget(self.lbl_summary)

        layout.addStretch()

        footer = QLabel(
            "بعد النقر على 'إنهاء' سيُعاد تشغيل نافذة تسجيل الدخول.\n"
            "Après avoir cliqué sur 'Terminer', la fenêtre de connexion s'affichera."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color: #777; font-style: italic; font-size: 11px;")
        layout.addWidget(footer)
        return w

    def _fill_summary(self):
        lines = [
            f"📌  اسم المدرسة: {self.txt_school_name.text().strip()}",
            f"📍  الموقع: {self.txt_school_location.text().strip() or '—'}",
            f"🗄️  قاعدة البيانات: {self.txt_db_user.text().strip()}@"
            f"{self.txt_db_host.text().strip()}:{self.spin_db_port.value()}"
            f"/{self.txt_db_name.text().strip()}",
            f"👤  المسؤول: {self.txt_admin_user.text().strip()}",
            f"💾  مجلد النسخ الاحتياطي: {self.txt_backup_path.text().strip()}",
        ]
        self.lbl_summary.setText("\n".join(lines))

    # ──────────────────────────── منطق التنقل ────────────────────────────────

    def _go_next(self):
        current = self.stack.currentIndex()
        if not self._validate_step(current):
            return
        if current == self.TOTAL_STEPS - 1:
            self._finish()
        else:
            self.stack.setCurrentIndex(current + 1)
            if self.stack.currentIndex() == self.TOTAL_STEPS - 1:
                self._fill_summary()
            self._update_nav()
            self._update_progress_bar()

    def _go_back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_nav()
            self._update_progress_bar()

    def _update_nav(self):
        idx = self.stack.currentIndex()
        self.btn_back.setEnabled(idx > 0)
        if idx == self.TOTAL_STEPS - 1:
            self.btn_next.setText("✅ إنهاء / Terminer")
        else:
            self.btn_next.setText("التالي / Suivant ►")

    def _validate_step(self, step: int) -> bool:
        """التحقق من صحة بيانات الخطوة الحالية"""
        if step == 1:  # معلومات المدرسة
            if not self.txt_school_name.text().strip():
                QMessageBox.warning(self, "خطأ", "اسم المدرسة مطلوب.")
                return False

        elif step == 2:  # قاعدة البيانات
            if not self.txt_db_pass.text():
                QMessageBox.warning(self, "خطأ", "كلمة مرور قاعدة البيانات مطلوبة.")
                return False

        elif step == 3:  # حساب المسؤول
            from validators import validate_password_strength
            admin_user = self.txt_admin_user.text().strip()
            if not admin_user:
                QMessageBox.warning(self, "خطأ", "اسم المستخدم المسؤول مطلوب.")
                return False
            pwd = self.txt_admin_pass.text()
            confirm = self.txt_admin_confirm.text()
            errors = validate_password_strength(pwd)
            if errors:
                from validators import format_errors
                QMessageBox.warning(self, "كلمة مرور ضعيفة", format_errors(errors))
                return False
            if pwd != confirm:
                QMessageBox.warning(self, "خطأ", "كلمتا المرور غير متطابقتين.")
                return False

        return True

    # ─────────────────────────── الحفظ النهائي ───────────────────────────────

    def _finish(self):
        """تطبيق جميع الإعدادات وإغلاق المعالج"""
        try:
            config = self.config

            # 1. معلومات المدرسة
            config.set("APPLICATION", "school_name", self.txt_school_name.text().strip())
            config.set("APPLICATION", "school_location", self.txt_school_location.text().strip())
            config.set("DATABASE", "backup_dir", self.txt_backup_path.text().strip())

            # 2. إعدادات قاعدة البيانات
            config.set("DATABASE", "host", self.txt_db_host.text().strip())
            config.set("DATABASE", "port", str(self.spin_db_port.value()))
            config.set("DATABASE", "dbname", self.txt_db_name.text().strip())
            config.set("DATABASE", "user", self.txt_db_user.text().strip())
            # تخزين كلمة المرور بأمان في keyring
            config.set_db_password(self.txt_db_pass.text())
            
            # 2b. الترحيل الآمن من config.ini إلى keyring (إذا كانت موجودة)
            config.migrate_password_to_keyring()

            # 3. تحديث كلمة مرور المسؤول في قاعدة البيانات
            self._update_admin_password()

            AppLogger.info("FirstRunWizard", "تم إكمال إعداد البرنامج الأول بنجاح")
            QMessageBox.information(
                self, "تم الإعداد / Configuration terminée",
                "تم حفظ جميع الإعدادات بنجاح!\n"
                "Configuration enregistrée avec succès!\n\n"
                "سيبدأ البرنامج الآن. / Le logiciel va démarrer maintenant."
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل حفظ الإعدادات: {e}")
            AppLogger.error("FirstRunWizard", f"فشل إنهاء الإعداد: {e}")

    def _update_admin_password(self):
        """تحديث كلمة مرور المسؤول في قاعدة البيانات"""
        new_username = self.txt_admin_user.text().strip()
        new_password = self.txt_admin_pass.text()

        if not new_password or new_password == "admin":
            return  # لم تُغيَّر كلمة المرور — نتجاهل

        try:
            import security_utils
            from database_setup import DatabaseManager, log_audit
            from repositories.login_repo import LoginRepository
            new_hash = security_utils.hash_password(new_password)
            db = DatabaseManager()
            with db.get_connection() as conn:
                LoginRepository(conn).update_admin_credentials(new_hash, new_username)
                conn.commit()
                log_audit(conn, "wizard", "ADMIN_SETUP", new_username)
        except Exception as e:
            AppLogger.warning("FirstRunWizard", f"لم يتم تحديث كلمة مرور المسؤول في DB: {e}")
            # لا نوقف العملية — ربما DB لم تُنشأ بعد


# ─────────────────────────────────────────────────────────────────────────────
# اختبار مستقل
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    print(f"should_run_wizard() = {should_run_wizard()}")

    wiz = FirstRunWizard()
    result = wiz.exec()
    print(f"Wizard result: {'Accepted' if result == QDialog.DialogCode.Accepted else 'Rejected'}")
    sys.exit(0)
