# -*- coding: utf-8 -*-
"""
Database Path Manager
Handles database path for both development and production environments
"""
import os
import sys
from pathlib import Path

def get_db_path():
    """
    Returns the appropriate database path based on environment
    Development: Uses current directory
    Production: Uses AppData folder for write permissions
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

# Global database path
DB_PATH = get_db_path()
BACKUP_DIR = get_backup_dir()
LOGS_DIR = get_logs_dir()
