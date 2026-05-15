"""
نظام إدارة الإعدادات الموحد
Configuration Manager System
"""

import configparser
import os
from pathlib import Path
import db_path
from app_logger import AppLogger


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
    
    def _create_default_config(self):
        """إنشاء ملف إعدادات افتراضي"""
        self._config['DATABASE'] = {
            'path': db_path.get_db_path(),
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
    
    # ================== اختصارات سريعة للإعدادات الشائعة ==================
    
    @property
    def db_path(self):
        return self.get('DATABASE', 'path', db_path.get_db_path())
    
    @property
    def database_path(self):
        return self.db_path # Alias
        
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
    print(f"مسار قاعدة البيانات: {config.db_path}")
    print(f"النسخ الاحتياطي التلقائي: {config.auto_backup_enabled}")
    print(f"الوضع الداكن: {config.dark_mode_enabled}")
    print(f"السجلات مفعلة: {config.logging_enabled}")
    
    print("\n✅ نظام الإعدادات يعمل بشكل صحيح وجاهز للاستخدام من كافة الشاشات.")