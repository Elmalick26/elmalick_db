# El Malick Gest - Workspace Instructions

## Project Overview

**El Malick Gest** is a comprehensive school/educational institution management system built with Python and PyQt6. It provides a modern desktop application with bilingual support (Arabic/French) for managing students, staff, finances, attendance, grades, and administrative operations.

---

## 1. Project Type & Purpose

**Type**: Educational/Institutional Management Desktop Application
**Main Purpose**: Comprehensive school management system with role-based access control
**Key Features**:

- Student and staff management (CRUD operations)
- Finance management (fees, payments, expenses, dashboards)
- Attendance tracking (students and staff)
- Grade management and bulletin generation
- Reporting and PDF exports
- User management with authentication
- System maintenance and automated backups
- Multi-user support with role-based permissions

**Target Environment**: Windows desktop (with PyInstaller distribution support)

---

## 2. Technology Stack

### Core Framework

- **Python 3** - Primary language
- **PyQt6** - Desktop GUI framework
- **SQLite3** - Database with foreign key constraints and WAL mode

### Libraries & Dependencies

| Category | Libraries |
|----------|-----------|
| **Visualization** | matplotlib (dashboards, charts) |
| **PDF/Export** | FPDF (report generation) |
| **Security** | bcrypt (password hashing) |
| **Data Processing** | numpy, pandas (via matplotlib) |
| **Images** | Pillow (PIL) |
| **System** | psycopg_binary, pytz, dateutil, charset_normalizer |
| **Build/Package** | PyInstaller, Inno Setup 6 |

### Virtual Environment

- Location: `.venv/` (project root)
- Python environment is pre-configured

---

## 3. Architecture

### High-Level Structure

```
El Malick Gest/
├── main_dashbord.py          # Entry point (MainWindow)
├── login_window.py           # Authentication
├── config_manager.py         # Configuration (Singleton)
├── database_setup.py         # Database manager (Singleton, Context Manager)
├── db_path.py               # Path management (dev vs production)
├── app_logger.py            # Logging system (Singleton)
├── ui_styles.py             # Theme & styling (Singleton)
├── security_utils.py        # Password hashing
│
├── Student & Academic Modules
│   ├── student_management.py
│   ├── student_attendance.py
│   ├── student_grades.py
│   ├── student_discipline.py
│   └── bulletin_generation.py
│
├── Staff Modules
│   ├── staff_management.py
│   ├── staff_attendance.py
│   └── staff_leaves.py
│
├── Finance Modules
│   ├── finance_fees_setup.py
│   ├── finance_payments.py
│   ├── finance_expenses.py
│   └── finance_dashboard.py
│
├── Administrative Modules
│   ├── academic_settings.py
│   ├── user_management.py
│   ├── admin_documents.py
│   ├── inventory_management.py
│   ├── communication_ui.py
│   ├── system_maintenance.py
│   ├── advanced_reports.py
│   ├── payment_management.py
│   └── year_end_migration.py
│
├── Support & Utilities
│   ├── print_export_service.py    # PDF/print orchestration
│   ├── pdf_report_style.py        # PDF styling
│   ├── auto_backup.py             # Automatic backups
│   ├── payment_management.py      # Payment tracking
│
├── Configuration & Data
│   ├── config.ini                 # Application configuration
│   ├── school_management.db       # SQLite database
│   └── logs/                      # Application logs
│
├── Distribution
│   ├── dist_release/              # PyInstaller output (.exe)
│   ├── build_release/             # PyInstaller build cache
│   └── backups/                   # Automated backups
│
└── Development
    ├── .venv/                     # Virtual environment
    └── .git/                      # Version control
```

### Key Architectural Patterns

#### 1. **Singleton Pattern** (Infrastructure)

Three core systems use Singleton pattern:

- **ConfigManager**: Centralized configuration from `config.ini`
- **AppLogger**: Unified logging to `logs/app_YYYYMMDD.log`
- **DatabaseManager**: Single database connection manager

#### 2. **Module Loading** (Modular UI)

- Main window uses **QStackedWidget** for switching between modules
- Modules dynamically imported in `main_dashbord.py` with exception handling
- Lazy instantiation: modules created only when user navigates to them
- Graceful degradation: missing modules don't crash the app (MODULES_AVAILABLE flag)

#### 3. **Context Manager Pattern** (Database)

```python
# Proper connection management
with DatabaseManager() as db:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        # Database operations
```

#### 4. **Theme Management**

- Centralized in `ui_styles.py`
- Light mode (Colors) and Dark mode (DarkColors) classes
- QSS stylesheets applied dynamically
- Theme persisted in `config.ini`

#### 5. **Environment Detection**

- **Development Mode**: Uses local `school_management.db` in project root
- **Production Mode** (Frozen/EXE): Uses `AppData/SchoolManagement/school_management.db`
- Detection via `sys.frozen` attribute (PyInstaller)
- Font paths configured for bundled fonts directory

---

## 4. Build/Run/Test Commands

### Running the Application

```powershell
# Activate virtual environment (if not already activated)
& ".venv/Scripts/Activate.ps1"

# Run the application
python main_dashbord.py
```

**First Login:**

- Username: `admin`
- Password: `admin`
- (Default admin account auto-created if no users exist)

### Building Windows Executable

```powershell
# Clean build with PyInstaller
python -m PyInstaller "El Malick Gest.spec" --noconfirm --clean --distpath dist_release --workpath build_release

# Output: dist_release/El Malick Gest/El Malick Gest.exe
```

**Note:** The `.spec` file is referenced in RELEASE_CHECKLIST.md but not shown in the repository. It defines PyInstaller configuration.

### Building Windows Installer

```powershell
# Requires Inno Setup 6 installed
& "C:\Users\EL MALICK\AppData\Local\Programs\Inno Setup 6\ISCC.exe" "ElMalickGestInstaller.iss"

# Output: installer_output/El_Malick_Gest_Setup.exe
```

### Pre-Release Validation

Refer to [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for comprehensive testing steps:

- [ ] Login functionality
- [ ] Student/staff CRUD operations
- [ ] Invoice and dues reports
- [ ] PDF report generation
- [ ] Arabic text rendering
- [ ] Application icon visibility

---

## 5. Key Conventions Unique to This Codebase

### Naming Conventions

- **Main dashboard**: `main_dashbord.py` (note: "dashbord" not "dashboard" - original spelling)
- **Window classes**: `ModernStudentManagement`, `StudentAttendanceWindow`, etc.
- **Module-level imports**: Bilingual comments in Arabic/French
- **Configuration sections**: UPPERCASE (DATABASE, APPLICATION, UI, SECURITY, etc.)

### Bilingual Support

- Arabic (ar) is the primary language setting in `config.ini`
- All comments and documentation are in Arabic/French
- Special font configuration required for RTL (Right-to-Left) text
- Environment variable: `QT_QPA_FONTDIR` set via `configure_qt_font_environment()`
- Bundled fonts in `Fonts/` directory (Amiri, Cairo, Noto Naskh Arabic)

### Coding Standards

- **Encoding**: UFT-8 throughout (explicitly specified in file operations)
- **Database Queries**: Parameterized (use `?` placeholders, never string concatenation)
- **Error Handling**: Try/except with fallbacks; graceful degradation
- **Context Managers**: Always use `with` for database/file operations
- **Module Comments**: Bilingual docstrings

### Configuration Management

- **File**: `config.ini` in project root
- **Auto-creation**: Default config created automatically if file missing
- **Singleton access**: `config = ConfigManager()`
- **No hardcoded paths**: All paths derived from `db_path.py` functions
- **Environment variables**: QT fonts configured automatically on startup

### Database

- **Type**: SQLite3 with enforced foreign keys
- **PRAGMA settings**:
  - `PRAGMA foreign_keys = ON;` - Enforce referential integrity
  - `PRAGMA journal_mode = WAL;` - Write-Ahead Logging for performance
- **Path Detection**: Automatic dev/production via `sys.frozen` check
- **Thread Safety**: Use context managers for all connections

### Logging

- **System**: AppLogger (Singleton)
- **Output**: Both file and console
- **Location**: `logs/app_YYYYMMDD.log`
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - [%(module)s] - %(message)s`
- **Encoding**: UTF-8 for Arabic/French support

### Security

- **Password Storage**: bcrypt hashing (from `security_utils.py`)
- **Authentication**: Login window with failed-attempt lockout
- **Default Credentials**: admin/admin (changed on first use recommended)
- **Session Timeout**: Configurable in UI settings (default 60 minutes)
- **Role-Based Access**: Users assigned to roles (Admin, Teacher, Staff, etc.)

### Common Development Patterns

**1. Module Import with Error Handling**

```python
try:
    from student_management import ModernStudentManagement
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    print(f"Import error: {e}")
```

**2. Configuration Access**

```python
config = ConfigManager()
app_name = config.app_name
dark_mode = config.dark_mode_enabled
```

**3. Database Operations**

```python
db = DatabaseManager()
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Students WHERE class_id = ?", (class_id,))
    results = cursor.fetchall()
```

**4. Logging**

```python
from app_logger import AppLogger
AppLogger.info("ModuleName", "Operation completed successfully")
AppLogger.error("ModuleName", f"Error occurred: {str(e)}")
```

**5. UI Styling**

```python
from ui_styles import ThemeManager, Colors
ThemeManager.apply_theme(self)  # Apply current theme
button.setStyleSheet(f"background-color: {Colors.PRIMARY};")
```

---

## 6. Common Development Patterns

### 1. Creating a New Feature Module

```python
# new_feature.py
import sys
import sqlite3
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from database_setup import DatabaseManager
from app_logger import AppLogger
from ui_styles import ThemeManager, Colors

class NewFeatureWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Feature Name")
        self.config = ConfigManager()
        
        # Apply theme
        ThemeManager.apply_theme(self)
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        # Build user interface
        pass
    
    def load_data(self):
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # Query database
            pass
```

### 2. Adding Database Tables

Edit `database_setup.py` to add SQL table creation in initialization. The app requires:

- Foreign key constraints
- Proper indexes for performance
- Audit columns (created_at, updated_at if needed)

### 3. Exporting Reports to PDF

Use `print_export_service.py` and `pdf_report_style.py`:

```python
from print_export_service import output_pdf
from pdf_report_style import apply_table_header_style

# Create report using FPDF
pdf = FPDF()
pdf.add_page()
# Add content...
output_pdf(pdf, "report_name.pdf")
```

### 4. Theme Implementation

All UI components should:

- Use QSS stylesheets for styling
- Reference `Colors`/`DarkColors` classes
- Call `ThemeManager.apply_theme(widget)` on initialization
- Support dynamic theme switching

### 5. Role-Based Access

After login, `MainWindow.__init__` receives:

- `username` - logged-in user
- `role` - user role (Admin, Teacher, Staff, etc.)

Use role to show/hide/disable features:

```python
if self.user_role == "Admin":
    # Show admin features
    pass
```

---

## 7. Configuration File Structure (config.ini)

```ini
[DATABASE]
path = school_management.db              # Auto-filled if not present
backup_dir = backups
auto_backup = True
backup_interval_hours = 24
retention_days = 30

[APPLICATION]
version = 1.0
icon_path = assets/app_icon.png
app_name = El Malick Gest
school_name = El Malick School Management System
school_location = 
theme = light                            # light or dark
debug_mode = False
language = ar                            # ar for Arabic, fr for French

[UI]
enable_dark_mode = False
auto_switch_dark_mode = False
dark_mode_schedule_enabled = False
dark_mode_start_time = 18:00
dark_mode_end_time = 06:00

[SECURITY]
password_min_length = 8
session_timeout_minutes = 60

[LOGGING]
enable_logging = True
log_level = INFO

[NOTIFICATIONS]
enable_notifications = True
```

**Notes:**

- All paths are relative unless `sys.frozen` (production mode)
- Configuration is auto-loaded and auto-saved by `ConfigManager`
- Changes persist across application restarts

---

## 8. Key Files for Reference

| File | Purpose |
|------|---------|
| `main_dashbord.py` | Application entry point and main window |
| `database_setup.py` | Database manager (Singleton, context managers) |
| `config_manager.py` | Configuration loader/saver (Singleton) |
| `db_path.py` | Path management for dev/production |
| `app_logger.py` | Logging system (Singleton) |
| `ui_styles.py` | Theme, colors, and QSS styling |
| `security_utils.py` | Password hashing with bcrypt |
| `login_window.py` | Authentication window |
| `config.ini` | Application configuration |
| `RELEASE_CHECKLIST.md` | Pre-release validation steps |

---

## 9. Common Issues & Solutions

### Issue: Application won't start

**Causes:**

- Virtual environment not activated
- Missing dependencies
- Database initialization failure

**Solution:**

```powershell
& ".venv/Scripts/Activate.ps1"
python -c "import PyQt6; print('PyQt6 OK')"
python main_dashbord.py
```

### Issue: Database errors

**Causes:**

- Permission issues on AppData (production mode)
- Foreign key constraint violations
- Stale database file

**Solution:**

- Delete `school_management.db` to force re-initialization
- Check `logs/app_*.log` for detailed errors
- Ensure write permissions in project directory

### Issue: Arabic text not rendering

**Causes:**

- Fonts directory not found
- QT_QPA_FONTDIR not set

**Solution:**

- Ensure `Fonts/` directory exists in dist bundle
- Check `db_path.get_fonts_dir()` in logs
- For development: Set `QT_QPA_FONTDIR` manually if needed

### Issue: PyInstaller build fails

**Causes:**

- Missing .spec file
- Incorrect Python path
- Hidden imports not specified

**Solution:**

- Ensure `.spec` file exists in project root
- Use full path to Python executable in .venv
- Add hidden imports in .spec file if needed

---

## 10. Development Workflow

### Setup New Development Environment

```powershell
# Clone or open repository
cd "El Malick Gest - Copie"

# Activate virtual environment
& ".venv/Scripts/Activate.ps1"

# Install/update dependencies (if needed)
pip install PyQt6 bcrypt fpdf matplotlib numpy

# Run application
python main_dashbord.py
```

### Making Code Changes

1. **Edit source files** - All .py files in project root (no subdirectories)
2. **Test in dev mode** - Run `python main_dashbord.py` to test changes
3. **Check logs** - Review `logs/app_*.log` for any issues
4. **Commit to git** - Stage and commit changes
5. **Build release** - Use PyInstaller command to build .exe when ready

### Debugging Tips

- **Enable debug mode**: Set `debug_mode = True` in config.ini
- **Check logs**: `logs/` directory contains daily log files
- **Use print statements**: Console output visible in terminal
- **Qt debugging**: Use PyQt6 property inspector or print widget tree
- **Database inspection**: Use SQLite3 CLI or GUI tool

---

## 11. Important Notes

✅ **Always use**:

- Context managers for database operations
- Parameterized queries (never string concatenation)
- ConfigManager for settings (not hardcoded values)
- AppLogger for logging (not print statements)

❌ **Never**:

- Hardcode database paths
- Use string-formatted SQL queries
- Access config.ini directly
- Create multiple database connections without cleanup

📝 **Remember**:

- Application is bilingual (Arabic/French)
- Built specifically for Windows with RTL text support
- Uses PyInstaller for distribution
- Singleton pattern for infrastructure components
- Role-based access control throughout

---

**Last Updated**: April 3, 2026
**Version**: 1.0
