# -*- coding: utf-8 -*-
"""
Database Path Manager
Gère les chemins de base de données pour les environnements de développement et de production
يدير مسار قاعدة البيانات وملحقاتها لتجنب أخطاء الصلاحيات عند تحويل البرنامج إلى ملف تنفيذي (EXE)
"""
import os
import sys
from pathlib import Path


def get_app_base_dir() -> Path:
    """Returns runtime base directory (project root in dev, bundle root in frozen mode)."""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_fonts_dir() -> str | None:
    """Find bundled fonts directory for Qt font discovery."""
    base = get_app_base_dir()
    for candidate in (base / 'Fonts', base / 'fonts'):
        if candidate.exists() and candidate.is_dir():
            return str(candidate)
    return None


def configure_qt_font_environment() -> str | None:
    """Sets QT_QPA_FONTDIR to a valid bundled fonts directory when available."""
    fonts_dir = get_fonts_dir()
    if fonts_dir and not os.environ.get('QT_QPA_FONTDIR'):
        os.environ['QT_QPA_FONTDIR'] = fonts_dir
    return fonts_dir

def get_db_path():
    """
    Returns the appropriate database path based on environment.
    Development: Uses current directory.
    Production: Uses AppData folder for write permissions.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Use AppData for user data (has write permissions)
        appdata = os.getenv('APPDATA') or os.path.expanduser('~')
        db_dir = Path(appdata) / 'SchoolManagement'
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / 'school_management.db')
    else:
        # Running in development mode
        return 'school_management.db'

def get_backup_dir():
    """Returns the backups directory path"""
    if getattr(sys, 'frozen', False):
        appdata = os.getenv('APPDATA') or os.path.expanduser('~')
        backup_dir = Path(appdata) / 'SchoolManagement' / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        return str(backup_dir)
    else:
        backup_dir = Path('backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        return str(backup_dir)

def get_logs_dir():
    """Returns the logs directory path"""
    if getattr(sys, 'frozen', False):
        appdata = os.getenv('APPDATA') or os.path.expanduser('~')
        logs_dir = Path(appdata) / 'SchoolManagement' / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        return str(logs_dir)
    else:
        logs_dir = Path('logs')
        logs_dir.mkdir(parents=True, exist_ok=True)
        return str(logs_dir)

# Global variables for easy access
DB_PATH = get_db_path()
BACKUP_DIR = get_backup_dir()
LOGS_DIR = get_logs_dir()