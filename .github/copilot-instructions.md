---
name: El Malick Gest
description: |
  Educational institution management system built with Python/PyQt6. 
  Desktop application for school operations: student/staff management, finances, 
  attendance, grades, reporting. Bilingual (Arabic/French), Windows-native with 
  PyInstaller distribution.
---

# El Malick Gest - AI Assistant Instructions

## Quick Start

**Run**: `python main_dashbord.py`
**Build**: `python -m PyInstaller "El Malick Gest.spec" --noconfirm --clean --distpath dist_release`
**Login**: `admin` / `admin` (default credentials)

See [WORKSPACE_INSTRUCTIONS.md](../WORKSPACE_INSTRUCTIONS.md) for complete guidance.

---

## Essential Context

### Technology Stack
- **Python 3** + **PyQt6** (GUI)
- **SQLite3** (database with foreign keys + WAL mode)
- **Matplotlib** (charts/dashboards)
- **FPDF** (PDF reports)
- **Bcrypt** (password hashing)
- **PyInstaller** (Windows .exe packaging)

### Project Structure
- **Flat layout**: All 30+ modules in root directory (no src/ subdirectories)
- **Singleton pattern**: ConfigManager, AppLogger, DatabaseManager
- **Dynamic module loading**: QStackedWidget switches between features
- **Context managers**: All database operations require `with` statements

### Architecture Patterns
1. **Module pattern**: Each feature is a `QMainWindow` class (e.g., `StudentManagementWindow`)
2. **Configuration**: Centralized `config.ini` accessed via `ConfigManager()` singleton
3. **Database**: Always use `with DatabaseManager().get_connection() as conn:`
4. **Logging**: Use `AppLogger.info()`, `AppLogger.error()` (not print statements)
5. **Theming**: All UI components call `ThemeManager.apply_theme(self)` and use `Colors` class

---

## Critical Coding Standards

### ✅ Always Do
- **Parameterized queries**: `cursor.execute("SELECT * FROM Students WHERE id = ?", (id,))`
- **Context managers**: `with DatabaseManager() as db: with db.get_connection() as conn:`
- **Use ConfigManager**: `config = ConfigManager(); value = config.setting_name`
- **Use AppLogger**: `AppLogger.info("ModuleName", "message")` for logging
- **UTF-8 encoding**: All file I/O must specify `encoding='utf-8'`
- **Bilingual comments**: Documents are in Arabic/French

### ❌ Never Do
- **String concatenation in SQL**: Query injection risk
- **Hardcoded paths**: Use `db_path.py` functions or ConfigManager
- **Direct config.ini access**: Always use `ConfigManager` singleton
- **Print statements for logging**: Use `AppLogger` instead
- **Multiple database connections**: Use context managers for cleanup

---

## Development Worklow

### Making Changes
1. Edit .py file in project root
2. Test: Run `python main_dashbord.py`
3. Check logs: `logs/app_*.log` for errors
4. Commit to git when ready

### Adding New Features
- Create new `XxxWindow` class inheriting `QMainWindow`
- Import and add to QStackedWidget in `main_dashbord.py`
- Use theme manager: `ThemeManager.apply_theme(self)`
- Database queries always use context managers

### Database Schema Changes
- Edit `database_setup.py` to add table creation SQL
- Include foreign keys and proper indexes
- Test schema creation by deleting `school_management.db` and restarting

---

## Important Conventions

### Naming
- Main file: `main_dashbord.py` (note original spelling: "dashbord" not "dashboard")
- Window classes: PascalCase ending in `Window` (e.g., `StudentAttendanceWindow`)
- Database functions: snake_case
- Configuration keys: UPPERCASE (DATABASE, APPLICATION, UI, SECURITY)

### Bilingual Support
- Primary language: Arabic (ar) in config.ini
- Environment: `QT_QPA_FONTDIR` auto-set for RTL fonts (Amiri, Cairo, Noto Naskh)
- System supports bidirectional text (Arabic/French/English)

### Database
- **Type**: SQLite3 in project root (dev) or `AppData/SchoolManagement/` (frozen/exe)
- **Requirements**: Foreign key constraints, write-ahead logging (WAL)
- **Thread-safe**: Use context managers for all operations
- **Detection**: Auto-switches dev/prod via `sys.frozen` attribute

### Configuration
- **File**: `config.ini` in project root (auto-created if missing)
- **Access**: `config = ConfigManager()` (singleton, thread-safe)
- **Sections**: DATABASE, APPLICATION, UI, SECURITY, LOGGING, NOTIFICATIONS
- **Persistence**: Auto-saved on changes; no manual save needed

### Theme & Styling
- **System**: Centralized in `ui_styles.py` (Colors, DarkColors, QSS stylesheets)
- **Apply to widgets**: `ThemeManager.apply_theme(widget)`
- **Colors**: Reference `Colors.PRIMARY`, `Colors.SECONDARY`, etc.
- **Dark mode**: Toggle in application settings; persists to config.ini

### Logging
- **System**: AppLogger singleton
- **Output**: File (`logs/app_YYYYMMDD.log`) + console; UTF-8 encoded
- **API**: `AppLogger.info("ModuleName", "message")`, `AppLogger.error(...)`
- **Format**: `timestamp - name - level - [module] - message`

### Security
- **Password storage**: bcrypt hashing (from `security_utils.py`)
- **Authentication**: Login window with role-based access control
- **Default account**: admin/admin (should be changed on first use)
- **Session timeout**: Configurable in UI settings (default 60 min)
- **Roles**: Admin, Teacher, Staff, Parent (controls feature visibility)

---

## Common Questions

**Q: Where do I add a new database table?**  
A: Edit `database_setup.py` and add SQL `CREATE TABLE` statements in the initialization function. Restart the app to create the table.

**Q: How do I query the database?**  
A: Use context managers:
```python
db = DatabaseManager()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Students WHERE class_id = ?", (class_id,))
    results = cursor.fetchall()
```

**Q: Where do I store application settings?**  
A: Use `ConfigManager()` singleton or add to `config.ini` sections. Never hardcode values.

**Q: How do I add logging?**  
A: Import and use: `AppLogger.info("ModuleName", "message")` or `AppLogger.error(...)`.

**Q: How do I debug the application?**  
A: Set `debug_mode = True` in config.ini, check `logs/app_*.log` files, add print statements to console.

**Q: How do I build the Windows .exe?**  
A: Run: `python -m PyInstaller "El Malick Gest.spec" --noconfirm --clean --distpath dist_release`

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `main_dashbord.py` | Application entry point and main UI |
| `login_window.py` | User authentication |
| `database_setup.py` | Database manager (Singleton, context-aware) |
| `config_manager.py` | Configuration manager (Singleton) |
| `db_path.py` | Path detection for dev vs production |
| `app_logger.py` | Logging system (Singleton) |
| `ui_styles.py` | Theme, colors, stylesheets |
| `security_utils.py` | Password hashing |
| `config.ini` | Application settings file |
| `WORKSPACE_INSTRUCTIONS.md` | Full project documentation |

---

## Troubleshooting

**Application won't start**: Check virtual environment is activated, dependencies installed, logs are readable.

**Database errors**: Check file permissions, delete `school_management.db` to force re-initialization, review logs.

**Arabic text not rendering**: Ensure `Fonts/` directory exists, `QT_QPA_FONTDIR` environment variable is set.

**PyInstaller build fails**: Verify `.spec` file exists, Python path is correct, hidden imports in .spec file.

---

**Last Updated**: April 3, 2026  
**For detailed guidance, see**: [WORKSPACE_INSTRUCTIONS.md](../WORKSPACE_INSTRUCTIONS.md)
