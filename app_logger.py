"""
نظام إدارة الأخطاء والسجلات الموحد
Unified Logging & Error Management System
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import db_path


class AppLogger:
    """نظام تسجيل موحد للتطبيق"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """إعداد نظام السجلات"""
        # إنشاء مجلد السجلات
        try:
            log_dir = Path(db_path.get_logs_dir())
        except AttributeError:
            # Fallback إذا لم تكن الدالة موجودة في db_path
            log_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
            
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # إعداد Logger
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        self._logger = logging.getLogger("SchoolApp")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        
        # File Handler - مع UTF-8 encoding
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console Handler - تأمين ضد بيئات التشغيل التي لا تحتوي على Console (مثل ملفات EXE)
        try:
            if sys.platform == 'win32' and hasattr(sys.stdout, 'fileno'):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.stream = open(sys.stdout.fileno(), mode='w', 
                                             encoding='utf-8', buffering=1)
            else:
                console_handler = logging.StreamHandler(sys.stdout)
        except Exception:
            console_handler = logging.StreamHandler()
        
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # إزالة المعالجات القديمة إن وجدت لتفادي التكرار
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
        
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
    
    @staticmethod
    def info(module, message):
        """تسجيل معلومة"""
        logger = AppLogger()
        logger._logger.info(f"[{module}] {message}")
    
    @staticmethod
    def error(module, message, exception=None):
        """تسجيل خطأ"""
        logger = AppLogger()
        if exception:
            logger._logger.error(f"[{module}] {message}", exc_info=exception)
        else:
            logger._logger.error(f"[{module}] {message}")
    
    @staticmethod
    def warning(module, message):
        """تسجيل تحذير"""
        logger = AppLogger()
        logger._logger.warning(f"[{module}] {message}")
    
    @staticmethod
    def debug(module, message):
        """تسجيل معلومة تصحيح"""
        logger = AppLogger()
        logger._logger.debug(f"[{module}] {message}")


class ErrorHandler:
    """معالج الأخطاء الموحد"""
    
    @staticmethod
    def handle_database_error(error, context=""):
        """معالجة أخطاء قاعدة البيانات"""
        import psycopg2
        
        if isinstance(error, psycopg2.OperationalError):
            message = f"Erreur de connexion: {error}"
            # في PostgreSQL، الخطأ التشغيلي غالباً يعني فقدان الاتصال بالخادم
            message = "فقدان الاتصال بقاعدة البيانات. تأكد من أن خادم PostgreSQL يعمل."
        elif isinstance(error, psycopg2.IntegrityError):
            message = f"Erreur d'intégrité / Integrity error: {error}"
        else:
            message = f"Erreur de base de données / Database error: {error}"
        
        AppLogger.error("ErrorHandler", f"[{context}] {message}", error)
        return message
    
    @staticmethod
    def handle_file_error(error, context=""):
        """معالجة أخطاء الملفات"""
        if isinstance(error, FileNotFoundError):
            message = f"الملف غير موجود: {error}"
        elif isinstance(error, PermissionError):
            message = f"لا توجد صلاحيات للوصول إلى الملف: {error}"
        else:
            message = f"خطأ في الملف: {error}"
        
        AppLogger.error("ErrorHandler", f"[{context}] {message}", error)
        return message
    
    @staticmethod
    def handle_validation_error(field, value, error_type):
        """معالجة أخطاء التحقق من البيانات"""
        messages = {
            "required": f"{field} مطلوب",
            "invalid_email": f"بريد إلكتروني غير صحيح: {value}",
            "invalid_phone": f"رقم هاتف غير صحيح: {value}",
            "invalid_number": f"قيمة رقمية غير صحيحة: {value}",
            "min_length": f"{field} يجب أن يكون أطول",
            "max_length": f"{field} يجب أن يكون أقصر",
            "duplicate": f"{field} موجود بالفعل: {value}"
        }
        
        message = messages.get(error_type, f"خطأ في التحقق: {error_type}")
        AppLogger.warning("ErrorHandler", f"[{field}] {message}")
        return message


# مثال على الاستخدام
if __name__ == "__main__":
    # إعداد السجلات
    logger = AppLogger()
    
    # تسجيل رسائل
    AppLogger.info("main", "البرنامج بدأ التشغيل")
    AppLogger.warning("main", "هذا تحذير تجريبي")
    AppLogger.debug("main", "هذه رسالة تصحيح")
    
    print("✅ نظام السجلات يعمل بشكل صحيح")
    print("📝 تحقق من ملف السجل في مجلد السجلات")