"""
نظام إدارة الإعدادات الموحد
Configuration Manager System
"""

import configparser
import os
from pathlib import Path
import db_path
from app_logger import AppLogger

# Keyring service name — مُعرِّف ثابت لتخزين البيانات في Windows Credential Manager
_KEYRING_SERVICE = "ElMalickGest"


class ConfigManager:
    """مدير الإعدادات المركزي (Singleton)"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
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
            pass  # صامت — الترحيل اختياري ولا يعيق التطبيق
    
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
            'retention_days': '30'
        }
        self._config['APPLICATION'] = {
            'version': '1.0',
            'icon_path': 'assets/app_icon.png',
            'app_name': 'El Malick Gest',
            'school_name': 'El Malick School Management System',
            'school_location': '',
            'theme': 'light',
            'debug_mode': 'False',
            'language': 'ar'
        }
        self._config['UI'] = {
            'enable_dark_mode': 'False',
            'auto_switch_dark_mode': 'False',
            'dark_mode_schedule_enabled': 'False',
            'dark_mode_start_time': '18:00',
            'dark_mode_end_time': '06:00'
        }
        self._config['SECURITY'] = {
            'password_min_length': '8',
            'session_timeout_minutes': '60'
        }
        self._config['LOGGING'] = {
            'enable_logging': 'True',
            'log_level': 'INFO'
        }
        self._config['NOTIFICATIONS'] = {
            'enable_notifications': 'True'
        }
        
        self._save_config()
    
    def get(self, section, key, fallback=None):
        """الحصول على قيمة إعداد (نصية)"""
        try:
            return self._config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_int(self, section, key, fallback=0):
        """الحصول على قيمة رقمية (صحيحة)"""
        try:
            return self._config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_bool(self, section, key, fallback=False):
        """الحصول على قيمة منطقية"""
        try:
            return self._config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_float(self, section, key, fallback=0.0):
        """الحصول على قيمة عشرية"""
        try:
            return self._config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def set(self, section, key, value):
        """تعيين قيمة إعداد"""
        if not self._config.has_section(section):
            self._config.add_section(section)
        
        self._config.set(section, key, str(value))
        self._save_config()
    
    def _save_config(self):
        """حفظ الإعدادات إلى الملف"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                self._config.write(f)
        except Exception as e:
            AppLogger.error("ConfigManager", f"فشل حفظ الإعدادات في {self.CONFIG_FILE}: {e}")
    
    # ================== اختصارات سريعة لإعدادات قاعدة البيانات ==================
    
    @property
    def db_host(self):
        return self.get('DATABASE', 'host', 'localhost')

    @property
    def db_port(self):
        return self.get_int('DATABASE', 'port', 5432)

    @property
    def db_name(self):
        return self.get('DATABASE', 'dbname', 'elmalick_db')

    @property
    def db_user(self):
        return self.get('DATABASE', 'user', 'postgres')

    @property
    def db_ssl_mode(self) -> str:
        """
        وضع SSL لاتصال PostgreSQL.
        القيم: 'disable' (تطوير) | 'require' | 'verify-ca' | 'verify-full' (إنتاج)
        يُعيَّن تلقائياً: 'disable' في بيئة التطوير، 'require' في بيئة الإنتاج.
        """
        # قراءة القيمة من config.ini إن وُجدت
        explicit = self.get('DATABASE', 'ssl_mode', '').strip()
        if explicit:
            return explicit
        # اكتشاف تلقائي: التطبيق مُجمَّع (PyInstaller) = إنتاج
        import sys
        return 'require' if getattr(sys, 'frozen', False) else 'disable'

    @property
    def db_password(self):
        """
        الحصول على كلمة مرور قاعدة البيانات.
        الأولوية: 1) keyring  2) متغير البيئة  3) config.ini (للتطوير فقط)
        """
        try:
            import keyring as _keyring
            stored = _keyring.get_password(_KEYRING_SERVICE, self.db_user)
            if stored:
                return stored
        except Exception:
            pass  # keyring غير متاح في بعض البيئات — نتجاهل الخطأ

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
        try:
            import keyring as _keyring
            _keyring.set_password(_KEYRING_SERVICE, self.db_user, password)
            # حذف كلمة المرور من config.ini بعد نقلها لـ keyring
            if self._config.has_option('DATABASE', 'password'):
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
        try:
            import keyring as _keyring
            # تحقق أولاً: إذا كانت keyring تحتوي بالفعل على كلمة مرور نتوقف
            existing = _keyring.get_password(_KEYRING_SERVICE, self.db_user)
            if existing:
                return True  # لا شيء يجب ترحيله
        except Exception:
            return False  # keyring غير متاح

        # اقرأ من config.ini
        plain_pass = self.get('DATABASE', 'password', '')
        placeholder = ('your_password_here', '', 'None', 'null')
        if plain_pass and plain_pass not in placeholder:
            return self.set_db_password(plain_pass)
        return False
        
    @property
    def backup_dir(self):
        return self.get('DATABASE', 'backup_dir', db_path.get_backup_dir())
    
    @property
    def auto_backup_enabled(self):
        return self.get_bool('DATABASE', 'auto_backup', True)

    @property
    def backup_interval_hours(self):
        return self.get_int('DATABASE', 'backup_interval_hours', 24)

    @property
    def backup_retention_days(self):
        return self.get_int('DATABASE', 'retention_days', 30)

    # ================== اختصارات سريعة لباقي الإعدادات ==================

    @property
    def app_name(self):
        return self.get('APPLICATION', 'app_name', 'El Malick Gest')

    @property
    def school_name(self):
        return self.get('APPLICATION', 'school_name', 'نظام إدارة المدرسة')

    @property
    def school_location(self):
        return self.get('APPLICATION', 'school_location', '')
    
    @property
    def debug_mode(self):
        return self.get_bool('APPLICATION', 'debug_mode', False)
    
    @property
    def language(self):
        return self.get('APPLICATION', 'language', 'ar')
    
    @property
    def theme(self):
        return self.get('APPLICATION', 'theme', 'light')
    
    @property
    def dark_mode_enabled(self):
        return self.get_bool('UI', 'enable_dark_mode', False)
        
    @property
    def enable_dark_mode(self):
        return self.dark_mode_enabled # Alias
    
    @property
    def auto_switch_dark_mode(self):
        return self.get_bool('UI', 'auto_switch_dark_mode', False)
        
    @property
    def dark_mode_schedule_enabled(self):
        return self.get_bool('UI', 'dark_mode_schedule_enabled', False)
    
    @property
    def dark_mode_start_time(self):
        return self.get('UI', 'dark_mode_start_time', '18:00')
    
    @property
    def dark_mode_end_time(self):
        return self.get('UI', 'dark_mode_end_time', '06:00')

    @property
    def password_min_length(self):
        return self.get_int('SECURITY', 'password_min_length', 8)
    
    @property
    def session_timeout(self):
        return self.get_int('SECURITY', 'session_timeout_minutes', 60)
    
    @property
    def logging_enabled(self):
        return self.get_bool('LOGGING', 'enable_logging', True)
    
    @property
    def log_level(self):
        return self.get('LOGGING', 'log_level', 'INFO')
    
    @property
    def enable_notifications(self):
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