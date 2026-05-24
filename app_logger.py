"""
نظام إدارة الأخطاء والسجلات الموحد
Unified Logging & Error Management System
"""

import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import db_path


def _build_extra(module: str, kwargs: dict) -> dict:
    """Build the 'extra' dict for structured log records."""
    extra: dict = {"app_module": module}
    if "user_id" in kwargs:
        extra["user_id"] = kwargs["user_id"]
    if "duration_ms" in kwargs:
        extra["duration_ms"] = kwargs["duration_ms"]
    return extra


class JSONLogFormatter(logging.Formatter):
    """Formatter that outputs one JSON object per line (JSONL)."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict = {
            "timestamp": datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "module": getattr(record, "app_module", record.module),
            "message": record.getMessage(),
        }
        user_id = getattr(record, "user_id", None)
        if user_id is not None:
            log_obj["user_id"] = user_id
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_obj["duration_ms"] = duration_ms
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


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

        # Text rotating file handler — 10 MB max, 7 backups
        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Console Handler — تأمين ضد بيئات التشغيل التي لا تحتوي على Console (مثل ملفات EXE)
        # ملاحظة: ملفات السجل (file handlers) تستخدم UTF-8 صراحةً وهي المصدر الرئيسي
        try:
            console_handler = logging.StreamHandler(sys.stdout)
        except Exception:
            console_handler = logging.StreamHandler()

        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # إزالة المعالجات القديمة إن وجدت لتفادي التكرار
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # JSON rotating log file — 10 MB max, 7 backups (JSONL format)
        json_log_file = log_dir / f"app_json_{datetime.now().strftime('%Y%m%d')}.jsonl"
        json_handler = RotatingFileHandler(json_log_file, maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8")
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONLogFormatter())

        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
        self._logger.addHandler(json_handler)

    @staticmethod
    def info(module, message, **kwargs):
        """تسجيل معلومة"""
        logger = AppLogger()
        logger._logger.info(f"[{module}] {message}", extra=_build_extra(module, kwargs))

    @staticmethod
    def error(module, message, exception=None, **kwargs):
        """تسجيل خطأ"""
        logger = AppLogger()
        if exception:
            logger._logger.error(
                f"[{module}] {message}",
                exc_info=exception,
                extra=_build_extra(module, kwargs),
            )
        else:
            logger._logger.error(f"[{module}] {message}", extra=_build_extra(module, kwargs))

    @staticmethod
    def warning(module, message, **kwargs):
        """تسجيل تحذير"""
        logger = AppLogger()
        logger._logger.warning(f"[{module}] {message}", extra=_build_extra(module, kwargs))

    @staticmethod
    def debug(module, message, **kwargs):
        """تسجيل معلومة تصحيح"""
        logger = AppLogger()
        logger._logger.debug(f"[{module}] {message}", extra=_build_extra(module, kwargs))


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
            "duplicate": f"{field} موجود بالفعل: {value}",
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
