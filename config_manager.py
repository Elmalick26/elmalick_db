"""
نظام إدارة الإعدادات الموحد
Configuration Manager System
"""

from __future__ import annotations

import configparser
import os
import sys
import threading
from pathlib import Path

import db_path
from app_logger import AppLogger

# Keyring service name — مُعرِّف ثابت لتخزين البيانات في Windows Credential Manager
_KEYRING_SERVICE = "ElMalickGest"

# محاولة واحدة فقط لاستيراد keyring — ليس حزمة إلزامية
try:
    import keyring as _keyring_lib

    _KEYRING_AVAILABLE = True
except ImportError:
    _keyring_lib = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False


class ConfigManager:
    """مدير الإعدادات المركزي (Singleton)"""

    _instance = None
    _config = None
    # FIX 1: Class-level lock for thread-safe singleton instantiation.
    # Without this, two threads starting simultaneously (e.g. AutoBackupSystem +
    # DatabaseManager both calling ConfigManager()) can both pass the
    # _instance is None check and call _load_config() twice — potentially
    # writing config.ini concurrently and corrupting it.
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking: re-verify inside lock in case another
                # thread completed initialization while we were waiting.
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    # تحديد مسار ملف الإعدادات ليكون بجانب سكربت البرنامج الرئيسي دائماً
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    cls._instance.CONFIG_FILE = os.path.join(base_dir, 'config.ini')
                    cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """تحميل الإعدادات من الملف"""
        self._config = configparser.ConfigParser()

        if os.path.exists(self.CONFIG_FILE):
            try:
                self._config.read(self.CONFIG_FILE, encoding='utf-8')
            except Exception as e:
                AppLogger.error("ConfigManager", f"خطأ في قراءة ملف الإعدادات، سيتم إنشاء ملف افتراضي: {e}")
                self._create_default_config()
        else:
            self._create_default_config()

        # محاولة الترحيل التلقائي من config.ini إلى keyring (بدون إزعاج المستخدم)
        try:
            self.migrate_password_to_keyring()
        except Exception as e:
            # FIX 2: Log instead of silently discarding — if migration fails,
            # the plaintext password stays in config.ini indefinitely with no
            # audit trail. A warning lets the administrator diagnose the cause.
            AppLogger.warning("ConfigManager", f"ترحيل كلمة المرور إلى Keyring فشل (تبقى في config.ini): {e}")

    def _create_default_config(self):
        """إنشاء ملف إعدادات افتراضي"""
        self._config['DATABASE'] = {
            'host': 'localhost',
            'port': '5432',
            'dbname': 'elmalick_db',
            'user': 'postgres',
            'password': 'your_password_here',
            'backup_dir': db_path.get_backup_dir(),
            'auto_backup': 'True',
            'backup_interval_hours': '24',
            'retention_days': '30',
        }
        self._config['APPLICATION'] = {
            'version': '1.0',
            'icon_path': 'assets/app_icon.png',
            'app_name': 'El Malick Gest',
            'school_name': 'El Malick School Management System',
            'school_location': '',
            'theme': 'light',
            'debug_mode': 'False',
            'language': 'ar',
        }
        self._config['UI'] = {
            'enable_dark_mode': 'False',
            'auto_switch_dark_mode': 'False',
            'dark_mode_schedule_enabled': 'False',
            'dark_mode_start_time': '18:00',
            'dark_mode_end_time': '06:00',
        }
        self._config['SECURITY'] = {'password_min_length': '8', 'session_timeout_minutes': '60'}
        self._config['LOGGING'] = {'enable_logging': 'True', 'log_level': 'INFO'}
        self._config['NOTIFICATIONS'] = {'enable_notifications': 'True'}

        self._save_config()

    def get(self, section: str, key: str, fallback: str | None = None) -> str | None:
        """الحصول على قيمة إعداد (نصية)"""
        try:
            return self._config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """الحصول على قيمة رقمية (صحيحة)"""
        try:
            return self._config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """الحصول على قيمة منطقية"""
        try:
            return self._config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """الحصول على قيمة عشرية"""
        try:
            return self._config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def set(self, section: str, key: str, value: object) -> None:
        """تعيين قيمة إعداد"""
        if not self._config.has_section(section):
            self._config.add_section(section)

        self._config.set(section, key, str(value))
        self._save_config()

    def _save_config(self) -> None:
        """حفظ الإعدادات إلى الملف"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                self._config.write(f)
        except Exception as e:
            AppLogger.error("ConfigManager", f"فشل حفظ الإعدادات في {self.CONFIG_FILE}: {e}")

    # ================== اختصارات سريعة لإعدادات قاعدة البيانات ==================

    @property
    def db_host(self) -> str:
        return self.get('DATABASE', 'host', 'localhost') or 'localhost'

    @property
    def db_port(self) -> int:
        return self.get_int('DATABASE', 'port', 5432)

    @property
    def db_name(self) -> str:
        return self.get('DATABASE', 'dbname', 'elmalick_db') or 'elmalick_db'

    @property
    def db_user(self) -> str:
        return self.get('DATABASE', 'user', 'postgres') or 'postgres'

    @property
    def db_ssl_mode(self) -> str:
        """
        وضع SSL لاتصال PostgreSQL.
        القيم: 'disable' (تطوير) | 'require' | 'verify-ca' | 'verify-full' (إنتاج)
        يُعيَّن تلقائياً: 'disable' في بيئة التطوير، 'require' في بيئة الإنتاج.
        """
        explicit = self.get('DATABASE', 'ssl_mode', '').strip()
        if explicit:
            return explicit
        # اكتشاف تلقائي: التطبيق مُجَمَّع (PyInstaller) = إنتاج
        return 'require' if getattr(sys, 'frozen', False) else 'disable'

    @property
    def db_password(self):
        """
        الحصول على كلمة مرور قاعدة البيانات.
        الأولوية: 1) keyring  2) متغير البيئة  3) config.ini (للتطوير فقط)
        """
        if _KEYRING_AVAILABLE:
            try:
                stored = _keyring_lib.get_password(_KEYRING_SERVICE, self.db_user)
                if stored:
                    return stored
            except Exception as e:
                # FIX 3: Log the fallback so administrators can diagnose why
                # the system is not reading from keyring (corrupt credential
                # store, permission denied, unsupported backend, etc.).
                AppLogger.warning("ConfigManager", f"تعذّر قراءة كلمة المرور من Keyring، سيتم استخدام البديل: {e}")

        # متغير البيئة (مفيد في بيئات CI/Docker)
        env_pass = os.environ.get("ELMALICK_DB_PASSWORD", "")
        if env_pass:
            return env_pass

        # fallback للـ config.ini (يبقى للتطوير المحلي)
        return self.get('DATABASE', 'password', '')

    def set_db_password(self, password: str) -> bool:
        """
        تخزين كلمة المرور في Windows Credential Manager عبر keyring
        وحذفها من config.ini لأمان أفضل.
        العائد: True إذا نجح التخزين.
        """
        if not _KEYRING_AVAILABLE:
            AppLogger.error("ConfigManager", "مكتبة keyring غير مثبتة — تعذّر تخزين كلمة المرور")
            return False
        try:
            _keyring_lib.set_password(_KEYRING_SERVICE, self.db_user, password)
            # حذف كلمة المرور من config.ini بعد نقلها لـ keyring
            if self._config is not None and self._config.has_option('DATABASE', 'password'):
                self._config.remove_option('DATABASE', 'password')
                self._save_config()
            AppLogger.info("ConfigManager", "تم تخزين كلمة مرور DB في Keyring بنجاح")
            return True
        except Exception as e:
            AppLogger.error("ConfigManager", f"فشل تخزين كلمة المرور في Keyring: {e}")
            return False

    def migrate_password_to_keyring(self) -> bool:
        """
        ترحيل كلمة المرور من config.ini إلى keyring.
        تُستدعى مرة واحدة عند الإعداد الأول أو من first_run_wizard.
        العائد: True إذا تمّ الترحيل أو لم يكن ضرورياً.
        """
        if not _KEYRING_AVAILABLE:
            return False  # keyring غير متاح
        try:
            # تحقق أولاً: إذا كانت keyring تحتوي بالفعل على كلمة مرور نتوقف
            existing = _keyring_lib.get_password(_KEYRING_SERVICE, self.db_user)
            if existing:
                return True  # لا شيء يجب ترحيله
        except Exception:
            return False

        # اقرأ من config.ini
        plain_pass = self.get('DATABASE', 'password', '')
        # FIX 4: Removed '' from placeholder — the `if plain_pass` truthiness
        # check already excludes empty strings before `not in` is evaluated.
        placeholder = ('your_password_here', 'None', 'null')
        if plain_pass and plain_pass not in placeholder:
            return self.set_db_password(plain_pass)
        return False

    @property
    def backup_dir(self) -> str:
        return self.get('DATABASE', 'backup_dir', db_path.get_backup_dir()) or db_path.get_backup_dir()

    @property
    def auto_backup_enabled(self) -> bool:
        return self.get_bool('DATABASE', 'auto_backup', True)

    @property
    def backup_interval_hours(self) -> int:
        return self.get_int('DATABASE', 'backup_interval_hours', 24)

    @property
    def backup_retention_days(self) -> int:
        return self.get_int('DATABASE', 'retention_days', 30)

    # ================== اختصارات سريعة لباقي الإعدادات ==================

    @property
    def app_name(self) -> str:
        return self.get('APPLICATION', 'app_name', 'El Malick Gest') or 'El Malick Gest'

    @property
    def school_name(self) -> str:
        return self.get('APPLICATION', 'school_name', 'نظام إدارة المدرسة') or 'نظام إدارة المدرسة'

    @property
    def school_location(self) -> str:
        return self.get('APPLICATION', 'school_location', '') or ''

    @property
    def debug_mode(self) -> bool:
        return self.get_bool('APPLICATION', 'debug_mode', False)

    @property
    def language(self) -> str:
        return self.get('APPLICATION', 'language', 'ar') or 'ar'

    @property
    def theme(self) -> str:
        return self.get('APPLICATION', 'theme', 'light') or 'light'

    @property
    def dark_mode_enabled(self) -> bool:
        return self.get_bool('UI', 'enable_dark_mode', False)

    @property
    def enable_dark_mode(self) -> bool:
        return self.dark_mode_enabled  # Alias

    @property
    def auto_switch_dark_mode(self) -> bool:
        return self.get_bool('UI', 'auto_switch_dark_mode', False)

    @property
    def dark_mode_schedule_enabled(self) -> bool:
        return self.get_bool('UI', 'dark_mode_schedule_enabled', False)

    @property
    def dark_mode_start_time(self) -> str:
        return self.get('UI', 'dark_mode_start_time', '18:00') or '18:00'

    @property
    def dark_mode_end_time(self) -> str:
        return self.get('UI', 'dark_mode_end_time', '06:00') or '06:00'

    @property
    def password_min_length(self) -> int:
        return self.get_int('SECURITY', 'password_min_length', 8)

    @property
    def session_timeout(self) -> int:
        return self.get_int('SECURITY', 'session_timeout_minutes', 60)

    @property
    def logging_enabled(self) -> bool:
        return self.get_bool('LOGGING', 'enable_logging', True)

    @property
    def log_level(self) -> str:
        return self.get('LOGGING', 'log_level', 'INFO') or 'INFO'

    @property
    def enable_notifications(self) -> bool:
        return self.get_bool('NOTIFICATIONS', 'enable_notifications', True)


# مثال للتجربة المستقلة
if __name__ == "__main__":
    config = ConfigManager()

    print("=== إعدادات التطبيق ===")
    print(f"اسم المدرسة: {config.school_name}")
    print(f"خادم قاعدة البيانات: {config.db_host}:{config.db_port}")
    print(f"اسم قاعدة البيانات: {config.db_name}")
    print(f"النسخ الاحتياطي التلقائي: {config.auto_backup_enabled}")
    print(f"الوضع الداكن: {config.dark_mode_enabled}")

    print("\n✅ نظام الإعدادات يعمل بشكل صحيح وجاهز للاستخدام مع خادم PostgreSQL.")
