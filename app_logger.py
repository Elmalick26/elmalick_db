"""
نظام إدارة الأخطاء والسجلات الموحد
Unified Logging & Error Management System
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
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
        # FIX 4: datetime.utcfromtimestamp() is deprecated in Python 3.12+
        # Use datetime.fromtimestamp with explicit UTC timezone instead
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        log_obj: dict = {
            "timestamp": ts,
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
    # FIX 2: Class-level lock ensures thread-safe singleton instantiation.
    # Without this, two threads (e.g. AnalyticsWorker + ReportWorker starting
    # simultaneously) could both pass the _instance is None check and call
    # _initialize() twice, adding 6 handlers instead of 3.
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking: re-check inside lock in case another
                # thread completed initialization while we were waiting
                if cls._instance is None:
                    cls._instance = super(AppLogger, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """إعداد نظام السجلات"""
        try:
            log_dir = Path(db_path.get_logs_dir())
        except AttributeError:
            log_dir = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))

        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

        self._logger = logging.getLogger("SchoolApp")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=7, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        try:
            console_handler = logging.StreamHandler(sys.stdout)
        except Exception:
            console_handler = logging.StreamHandler()

        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

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
        """تسجيل خطأ

        Pass `exception` when you have an Exception object and want its full
        traceback captured in the log — works whether or not you are inside
        an active `except` block.
        """
        logger = AppLogger()
        if exception is not None:
            # FIX 1: exc_info= accepts True (captures sys.exc_info()) or a
            # (type, value, traceback) 3-tuple.  Passing an Exception object
            # directly is NOT documented and silently drops the traceback when
            # called outside an active except block (sys.exc_info() returns
            # (None, None, None)).  Using the 3-tuple is deterministic and
            # always captures the real stack trace.
            exc_info = (type(exception), exception, exception.__traceback__)
            logger._logger.error(
                f"[{module}] {message}",
                exc_info=exc_info,
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
            # FIX 3: The original code assigned f"Erreur de connexion: {error}" then
            # immediately overwrote it with a generic Arabic string — the specific
            # error detail (e.g. "authentication failed" vs "connection refused")
            # was silently discarded. Now both the user-facing label and the DB
            # error text are preserved in the same message.
            message = f"فقدان الاتصال بقاعدة البيانات: {error}"
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


if __name__ == "__main__":
    logger = AppLogger()

    AppLogger.info("main", "البرنامج بدأ التشغيل")
    AppLogger.warning("main", "هذا تحذير تجريبي")
    AppLogger.debug("main", "هذه رسالة تصحيح")

    print("✅ نظام السجلات يعمل بشكل صحيح")
    print("📝 تحقق من ملف السجل في مجلد السجلات")
