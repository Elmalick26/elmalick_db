# -*- coding: utf-8 -*-
"""
Path Manager
Gère les chemins pour les logs, sauvegardes et ressources (polices).
(Le chemin de la base de données a été retiré suite à la migration vers PostgreSQL)
يدير مسارات الملحقات (النسخ الاحتياطي، السجلات، والخطوط).
(تم إزالة مسار قاعدة البيانات لأن PostgreSQL يعمل كخادم مستقل)
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

def find_pg_tool(tool_name: str) -> str:
    """
    Returns the full path of a PostgreSQL tool (pg_dump, pg_restore, psql).
    Searches PATH first, then common Windows installation directories.
    Raises FileNotFoundError if not found.
    """
    import shutil
    import glob

    # 1. Try PATH first
    found = shutil.which(tool_name)
    if found:
        return found

    # 2. Search common PostgreSQL installation paths on Windows
    search_patterns = [
        rf"C:\Program Files\PostgreSQL\*\bin\{tool_name}.exe",
        rf"C:\Program Files (x86)\PostgreSQL\*\bin\{tool_name}.exe",
        rf"C:\PostgreSQL\*\bin\{tool_name}.exe",
    ]
    for pattern in search_patterns:
        matches = sorted(glob.glob(pattern), reverse=True)  # newest version first
        if matches:
            return matches[0]

    raise FileNotFoundError(
        f"L'outil PostgreSQL '{tool_name}' est introuvable.\n"
        f"Assurez-vous que PostgreSQL est installé et que son dossier bin "
        f"(ex: C:\\Program Files\\PostgreSQL\\16\\bin) est dans le PATH."
    )


# Global variables for easy access (DB_PATH removed for PostgreSQL)
BACKUP_DIR = get_backup_dir()
LOGS_DIR = get_logs_dir()