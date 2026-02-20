import sqlite3
import os
import logging
from contextlib import contextmanager
from db_path import DB_PATH

# استخدام Logger قياسي وسيتولى AppLogger إدارته لاحقاً
logger = logging.getLogger("DatabaseManager")

class DatabaseManager:
    """
    مدير مركزي لقاعدة البيانات لضمان:
    1. تفعيل Foreign Keys دائماً.
    2. إدارة الاتصالات والإغلاق الآمن (Context Manager).
    3. توحيد مصدر الحقيقة لهيكلة البيانات.
    """
    
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = DB_PATH
            try:
                from config_manager import ConfigManager

                config = ConfigManager()
                config_path = config.db_path
                if config_path:
                    self.db_path = config_path
            except Exception:
                self.db_path = DB_PATH
        self._conn = None

    def __enter__(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode = WAL;")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            if exc_type:
                self._conn.rollback()
            self._conn.close()
            self._conn = None

    def get_connection(self):
        """
        Returns the active connection if in a context manager,
        otherwise returns a context manager to create one.
        """
        if self._conn:
            return self._conn
        return self._connection_context()

    @contextmanager
    def _connection_context(self):
        """
        Generates a safe database connection with Foreign Keys enabled.
        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                ...
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # تفعيل تكامل البيانات والعلاقات
            conn.execute("PRAGMA foreign_keys = ON;")
            # تحسين الأداء قليلاً
            conn.execute("PRAGMA journal_mode = WAL;") 
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database Error: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def initialize_database(self):
        """إنشاء جميع الجداول المطلوبة للنظام دفعة واحدة"""
        logger.info("🔄 جاري تهيئة قاعدة البيانات والتحقق من الهيكلة...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # --- 1. System & Users ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'User',
                    status TEXT DEFAULT 'Actif',
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (staff_id) REFERENCES Staff(id) ON DELETE SET NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AuditLogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT,
                    action TEXT,
                    target TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS EmailSettings (
                    id INTEGER PRIMARY KEY,
                    smtp_server TEXT,
                    smtp_port TEXT,
                    email_address TEXT,
                    email_password TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS NotificationLogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_type TEXT,
                    recipient_contact TEXT,
                    subject TEXT,
                    status TEXT,
                    error_msg TEXT,
                    sent_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SchoolInfo (
                    id INTEGER PRIMARY KEY,
                    republic TEXT, ia TEXT, ief TEXT, school_name TEXT, 
                    auth_number TEXT, address TEXT, phone TEXT, logo_path TEXT, director_name TEXT
                )
            """)

            # --- 2. Academic Structure ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AcademicYears (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year_label TEXT UNIQUE NOT NULL,
                    is_active INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_ar TEXT,
                    name_fr TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER,
                    class_name_ar TEXT,
                    class_name_fr TEXT,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (cycle_id) REFERENCES Cycles(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AcademicPeriods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year_id INTEGER,
                    cycle_id INTEGER,
                    period_name_ar TEXT,
                    period_name_fr TEXT,
                    sort_order INTEGER,
                    FOREIGN KEY (year_id) REFERENCES AcademicYears(id),
                    FOREIGN KEY (cycle_id) REFERENCES Cycles(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id INTEGER,
                    subject_name_ar TEXT,
                    subject_name_fr TEXT,
                    coefficient REAL DEFAULT 1,
                    subject_lang TEXT DEFAULT 'Français',
                    FOREIGN KEY (cycle_id) REFERENCES Cycles(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AssessmentTypes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_id INTEGER,
                    name_ar TEXT,
                    name_fr TEXT,
                    type_code TEXT,
                    weight_percentage REAL DEFAULT 1.0,
                    FOREIGN KEY (period_id) REFERENCES AcademicPeriods(id)
                )
            """)

            # --- 3. People (Students & Staff) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name_fr TEXT NOT NULL, last_name_fr TEXT NOT NULL,
                    first_name_ar TEXT NOT NULL, last_name_ar TEXT NOT NULL,
                    birth_date DATE, birth_place TEXT,
                    gender INTEGER, address TEXT,
                    parent_name TEXT, parent_phone TEXT, parent_email TEXT, parent_address TEXT,
                    class_id INTEGER,
                    registration_date DATE,
                    status TEXT DEFAULT 'Active',
                    photo_path TEXT,
                    FOREIGN KEY (class_id) REFERENCES Classes (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StudentClassNumbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    class_id INTEGER,
                    year_id INTEGER,
                    class_number INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES Students (id) ON DELETE CASCADE,
                    FOREIGN KEY (class_id) REFERENCES Classes (id),
                    FOREIGN KEY (year_id) REFERENCES AcademicYears (id),
                    UNIQUE (student_id, year_id),
                    UNIQUE (class_id, year_id, class_number)
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT,
                    last_name TEXT,
                    role TEXT,
                    specialty TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    hire_date TEXT,
                    contract_type TEXT DEFAULT 'Monthly',
                    salary_base REAL DEFAULT 0,
                    hourly_rate REAL DEFAULT 0,
                    photo_path TEXT,
                    status TEXT DEFAULT 'Actif'
                )
            """)

            # --- 4. Academic Data (Grades, Attendance, Discipline) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    subject_id INTEGER,
                    assessment_id INTEGER,
                    score REAL,
                    observation TEXT,
                    date_recorded TEXT,
                    year_id INTEGER,
                    FOREIGN KEY(student_id) REFERENCES Students(id) ON DELETE CASCADE,
                    FOREIGN KEY(subject_id) REFERENCES Subjects(id),
                    FOREIGN KEY(assessment_id) REFERENCES AssessmentTypes(id),
                    FOREIGN KEY(year_id) REFERENCES AcademicYears(id)
                )
            """)

            # Grades Indexes
            index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_grades_student_subject ON Grades(student_id, subject_id)",
                "CREATE INDEX IF NOT EXISTS idx_grades_assessment ON Grades(assessment_id)",
                "CREATE INDEX IF NOT EXISTS idx_grades_date ON Grades(date_recorded)",
                "CREATE INDEX IF NOT EXISTS idx_grades_year ON Grades(year_id)"
            ]
            for stmt in index_statements:
                cursor.execute(stmt)

            cursor.execute("""
               CREATE TABLE IF NOT EXISTS StudentAttendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    date DATE,
                    status TEXT,
                    justifie INTEGER DEFAULT 0,
                    reason TEXT,
                    notes TEXT,
                    year_id INTEGER,
                    recorded_by TEXT,
                    FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE CASCADE,
                    FOREIGN KEY (year_id) REFERENCES AcademicYears(id)
               ) 
            """)

            cursor.execute("""
               CREATE TABLE IF NOT EXISTS StaffAttendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                          attendance_date TEXT,
                          check_in_time TEXT,
                          check_out_time TEXT,
                          status TEXT,
                          note TEXT,
                    FOREIGN KEY (staff_id) REFERENCES Staff(id)
               ) 
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StaffLeaves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    leave_type TEXT, 
                    start_date DATE,
                    end_date DATE,
                    days_count INTEGER,
                    reason TEXT,
                    status TEXT DEFAULT 'En Attente',
                    FOREIGN KEY(staff_id) REFERENCES Staff(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StudentDiscipline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    incident_date DATE,
                    incident_type TEXT,
                    sanction TEXT,
                    points_deducted REAL DEFAULT 0,
                    observation TEXT,
                    year_id INTEGER,
                    FOREIGN KEY (student_id) REFERENCES Students(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Timetable (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    day_of_week TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    subject_id INTEGER,
                    teacher_id INTEGER,
                    room TEXT,
                    FOREIGN KEY (class_id) REFERENCES Classes(id),
                    FOREIGN KEY (subject_id) REFERENCES Subjects(id),
                    FOREIGN KEY (teacher_id) REFERENCES Staff(id)
                )
            """)

            # --- 5. Finance ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RegistrationFees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    amount REAL,
                    FOREIGN KEY (class_id) REFERENCES Classes(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MonthlyFeeSchedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    month_index INTEGER,
                    month_name TEXT,
                    amount REAL,
                    FOREIGN KEY (class_id) REFERENCES Classes(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    transaction_date TEXT,
                    total_due REAL,
                    discount REAL,
                    amount_paid REAL,
                    remaining_balance REAL,
                    payment_type TEXT, 
                    details TEXT, 
                    FOREIGN KEY (student_id) REFERENCES Students(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MonthlyPaymentsStatus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    month_index INTEGER, 
                    payment_id INTEGER,
                    amount_paid REAL,
                    FOREIGN KEY (student_id) REFERENCES Students(id),
                    FOREIGN KEY (payment_id) REFERENCES Payments(id)
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    amount REAL,
                    description TEXT,
                    expense_date DATE,
                    paid_to TEXT,
                    created_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SalarySlips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER,
                    month_str TEXT,
                    basic_amount REAL,
                    hours_worked REAL,
                    bonuses REAL,
                    deductions REAL,
                    net_amount REAL,
                    payment_date TEXT,
                    FOREIGN KEY (staff_id) REFERENCES Staff(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS InventoryItems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_fr TEXT,
                    name_ar TEXT,
                    category TEXT, 
                    quantity INTEGER DEFAULT 0,
                    min_quantity INTEGER DEFAULT 5,
                    unit_price REAL DEFAULT 0.0,
                    location TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS InventoryLog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER,
                    transaction_type TEXT, -- IN, OUT
                    quantity INTEGER,
                    transaction_date TEXT,
                    notes TEXT,
                    performed_by TEXT,
                    expense_id INTEGER,
                    FOREIGN KEY (item_id) REFERENCES InventoryItems(id)
                )
            """)

            # Core reporting indexes (must be created after all target tables exist)
            reporting_index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_students_class_status ON Students(class_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_student_class_numbers_year_student ON StudentClassNumbers(year_id, student_id)",
                "CREATE INDEX IF NOT EXISTS idx_assessment_period ON AssessmentTypes(period_id)",
                "CREATE INDEX IF NOT EXISTS idx_academic_periods_year_cycle_sort ON AcademicPeriods(year_id, cycle_id, sort_order)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_student_year_status ON StudentAttendance(student_id, year_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_year ON StudentAttendance(year_id)",
                "CREATE INDEX IF NOT EXISTS idx_discipline_student_year ON StudentDiscipline(student_id, year_id)",
                "CREATE INDEX IF NOT EXISTS idx_discipline_year ON StudentDiscipline(year_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_date ON Payments(transaction_date)",
                "CREATE INDEX IF NOT EXISTS idx_expenses_date ON Expenses(expense_date)"
            ]
            for stmt in reporting_index_statements:
                cursor.execute(stmt)

            # --- حفظ التغييرات ---
            conn.commit()
            logger.info("✅ قاعدة البيانات جاهزة ومحدثة (All structures verified).")

# عند تشغيل الملف مباشرة
if __name__ == "__main__":
    db = DatabaseManager()
    db.initialize_database()