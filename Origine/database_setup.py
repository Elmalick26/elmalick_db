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
            else:
                self._conn.commit()
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
                try:
                    conn.commit()
                except sqlite3.Error:
                    pass
                conn.close()

    def initialize_database(self):
        """إنشاء جميع الجداول المطلوبة للنظام دفعة واحدة"""
        logger.info("🔄 جاري تهيئة قاعدة البيانات والتحقق من الهيكلة...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()

            def _table_columns(table_name):
                cursor.execute(f"PRAGMA table_info({table_name})")
                return [row[1] for row in cursor.fetchall()]

            def _column_exists(table_name, column_name):
                return column_name in _table_columns(table_name)

            def _ensure_column(table_name, column_name, column_sql):
                if not _column_exists(table_name, column_name):
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
                    logger.info(f"🛠️ Migration: Added missing column {table_name}.{column_name}")

            def _safe_execute(sql, params=()):
                try:
                    cursor.execute(sql, params)
                except sqlite3.OperationalError as err:
                    logger.warning(f"Migration statement skipped: {sql} -> {err}")
            
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
                    gender TEXT, -- تم التعديل إلى TEXT لتخزين 'M' أو 'F'
                    address TEXT,
                    parent_name TEXT, parent_phone TEXT, parent_email TEXT, parent_address TEXT,
                    -- تمت إزالة class_id من هنا
                    registration_date DATE DEFAULT CURRENT_DATE, -- إضافة افتراضية لتاريخ اليوم
                    status TEXT DEFAULT 'Active',
                    photo_path TEXT
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
                          period_id INTEGER,
                    recorded_by TEXT,
                    FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE CASCADE,
                          FOREIGN KEY (year_id) REFERENCES AcademicYears(id),
                          FOREIGN KEY (period_id) REFERENCES AcademicPeriods(id)
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
                    period_id INTEGER,
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
                    year_id INTEGER, -- تمت الإضافة
                    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_due REAL,
                    discount REAL DEFAULT 0,
                    amount_paid REAL,
                    remaining_balance REAL,
                    payment_type TEXT, 
                    details TEXT, 
                    FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE RESTRICT,
                    FOREIGN KEY (year_id) REFERENCES AcademicYears(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS MonthlyPaymentsStatus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    month_index INTEGER, 
                    due_id INTEGER,
                    payment_id INTEGER,
                    amount_paid REAL,
                    FOREIGN KEY (student_id) REFERENCES Students(id),
                    FOREIGN KEY (due_id) REFERENCES StudentDues(id),
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS StudentDues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    year_id INTEGER,
                    fee_type TEXT, -- مثلاً: 'Registration', 'Month 1', 'Transport'
                    fee_description TEXT,
                    original_amount REAL,
                    discount_amount REAL DEFAULT 0,
                    net_amount REAL, -- المبلغ النهائي المطلوب بعد الخصم
                    due_date DATE,
                    is_paid INTEGER DEFAULT 0, -- 0 يعني لم يدفع، 1 يعني دُفع بالكامل
                    FOREIGN KEY (student_id) REFERENCES Students(id),
                    FOREIGN KEY (year_id) REFERENCES AcademicYears(id)
                )
            """)

            # --- 5.b Schema Migrations (backward compatibility) ---
            # AcademicYears legacy support: year_name/start_date/end_date -> year_label
            _ensure_column("AcademicYears", "year_label", "TEXT")
            academic_year_cols = _table_columns("AcademicYears")
            if "year_name" in academic_year_cols:
                _safe_execute("""
                    UPDATE AcademicYears
                    SET year_label = COALESCE(NULLIF(year_label, ''), year_name)
                    WHERE year_label IS NULL OR year_label = ''
                """)
            if "start_date" in academic_year_cols and "end_date" in academic_year_cols:
                _safe_execute("""
                    UPDATE AcademicYears
                    SET year_label = COALESCE(
                        NULLIF(year_label, ''),
                        strftime('%Y', start_date) || '-' || strftime('%Y', end_date)
                    )
                    WHERE year_label IS NULL OR year_label = ''
                """)

            # Staff legacy support: staff_name/position/salary -> first_name,last_name,role,salary_base
            _ensure_column("Staff", "first_name", "TEXT")
            _ensure_column("Staff", "last_name", "TEXT")
            _ensure_column("Staff", "role", "TEXT")
            _ensure_column("Staff", "specialty", "TEXT")
            _ensure_column("Staff", "address", "TEXT")
            _ensure_column("Staff", "contract_type", "TEXT DEFAULT 'Monthly'")
            _ensure_column("Staff", "salary_base", "REAL DEFAULT 0")
            _ensure_column("Staff", "hourly_rate", "REAL DEFAULT 0")
            _ensure_column("Staff", "photo_path", "TEXT")

            staff_cols = _table_columns("Staff")
            if "staff_name" in staff_cols:
                _safe_execute("""
                    UPDATE Staff
                    SET first_name = COALESCE(NULLIF(first_name, ''), staff_name)
                    WHERE first_name IS NULL OR first_name = ''
                """)
            _safe_execute("""
                UPDATE Staff
                SET last_name = COALESCE(NULLIF(last_name, ''), '')
                WHERE last_name IS NULL
            """)
            if "position" in staff_cols:
                _safe_execute("""
                    UPDATE Staff
                    SET role = COALESCE(NULLIF(role, ''), position)
                    WHERE role IS NULL OR role = ''
                """)
            if "salary" in staff_cols:
                _safe_execute("""
                    UPDATE Staff
                    SET salary_base = COALESCE(salary_base, salary)
                    WHERE salary_base IS NULL OR salary_base = 0
                """)

            # Students legacy support: student_name/class_id old schema -> multilingual names + SCN mapping
            _ensure_column("Students", "first_name_fr", "TEXT")
            _ensure_column("Students", "last_name_fr", "TEXT")
            _ensure_column("Students", "first_name_ar", "TEXT")
            _ensure_column("Students", "last_name_ar", "TEXT")
            _ensure_column("Students", "birth_place", "TEXT")
            _ensure_column("Students", "parent_email", "TEXT")
            _ensure_column("Students", "parent_address", "TEXT")
            _ensure_column("Students", "registration_date", "DATE")
            _ensure_column("Students", "photo_path", "TEXT")

            student_cols = _table_columns("Students")
            if "student_name" in student_cols:
                _safe_execute("""
                    UPDATE Students
                    SET first_name_fr = COALESCE(NULLIF(first_name_fr, ''), student_name)
                    WHERE first_name_fr IS NULL OR first_name_fr = ''
                """)
            _safe_execute("""
                UPDATE Students
                SET first_name_fr = COALESCE(NULLIF(first_name_fr, ''), 'Élève')
                WHERE first_name_fr IS NULL OR first_name_fr = ''
            """)
            _safe_execute("""
                UPDATE Students
                SET last_name_fr = COALESCE(last_name_fr, '')
                WHERE last_name_fr IS NULL
            """)
            _safe_execute("""
                UPDATE Students
                SET first_name_ar = COALESCE(first_name_ar, '')
                WHERE first_name_ar IS NULL
            """)
            _safe_execute("""
                UPDATE Students
                SET last_name_ar = COALESCE(last_name_ar, '')
                WHERE last_name_ar IS NULL
            """)

            # RegistrationFees/MonthlyFeeSchedule legacy support: cycle_id -> class_id
            _ensure_column("RegistrationFees", "class_id", "INTEGER")
            _ensure_column("MonthlyFeeSchedule", "class_id", "INTEGER")
            _ensure_column("MonthlyFeeSchedule", "month_name", "TEXT")

            reg_cols = _table_columns("RegistrationFees")
            if "cycle_id" in reg_cols:
                _safe_execute("""
                    UPDATE RegistrationFees
                    SET class_id = (
                        SELECT id FROM Classes c
                        WHERE c.cycle_id = RegistrationFees.cycle_id
                        ORDER BY c.sort_order, c.id
                        LIMIT 1
                    )
                    WHERE (class_id IS NULL OR class_id = 0) AND cycle_id IS NOT NULL
                """)

            mfs_cols = _table_columns("MonthlyFeeSchedule")
            if "cycle_id" in mfs_cols:
                _safe_execute("""
                    UPDATE MonthlyFeeSchedule
                    SET class_id = (
                        SELECT id FROM Classes c
                        WHERE c.cycle_id = MonthlyFeeSchedule.cycle_id
                        ORDER BY c.sort_order, c.id
                        LIMIT 1
                    )
                    WHERE (class_id IS NULL OR class_id = 0) AND cycle_id IS NOT NULL
                """)
            _safe_execute("""
                UPDATE MonthlyFeeSchedule
                SET month_name = COALESCE(NULLIF(month_name, ''), 'Mois ' || month_index)
                WHERE month_name IS NULL OR month_name = ''
            """)

            # StaffAttendance legacy support: date/notes -> attendance_date/note
            _ensure_column("StaffAttendance", "attendance_date", "TEXT")
            _ensure_column("StaffAttendance", "check_in_time", "TEXT")
            _ensure_column("StaffAttendance", "check_out_time", "TEXT")
            _ensure_column("StaffAttendance", "status", "TEXT")
            _ensure_column("StaffAttendance", "note", "TEXT")
            staff_att_cols = _table_columns("StaffAttendance")
            if "date" in staff_att_cols:
                _safe_execute("""
                    UPDATE StaffAttendance
                    SET attendance_date = COALESCE(NULLIF(attendance_date, ''), date)
                    WHERE attendance_date IS NULL OR attendance_date = ''
                """)
            if "notes" in staff_att_cols:
                _safe_execute("""
                    UPDATE StaffAttendance
                    SET note = COALESCE(NULLIF(note, ''), notes)
                    WHERE note IS NULL OR note = ''
                """)

            # InventoryLog legacy support: trasaction_type/action -> transaction_type
            _ensure_column("InventoryLog", "transaction_type", "TEXT")
            _ensure_column("InventoryLog", "quantity", "INTEGER")
            _ensure_column("InventoryLog", "transaction_date", "TEXT")
            _ensure_column("InventoryLog", "notes", "TEXT")
            inv_cols = _table_columns("InventoryLog")
            if "trasaction_type" in inv_cols:
                _safe_execute("""
                    UPDATE InventoryLog
                    SET transaction_type = COALESCE(NULLIF(transaction_type, ''), trasaction_type)
                    WHERE transaction_type IS NULL OR transaction_type = ''
                """)
            if "action" in inv_cols:
                _safe_execute("""
                    UPDATE InventoryLog
                    SET transaction_type = COALESCE(NULLIF(transaction_type, ''), action)
                    WHERE transaction_type IS NULL OR transaction_type = ''
                """)
            if "quantity_change" in inv_cols:
                _safe_execute("""
                    UPDATE InventoryLog
                    SET quantity = COALESCE(quantity, quantity_change)
                    WHERE quantity IS NULL
                """)
            if "date_time" in inv_cols:
                _safe_execute("""
                    UPDATE InventoryLog
                    SET transaction_date = COALESCE(NULLIF(transaction_date, ''), date_time)
                    WHERE transaction_date IS NULL OR transaction_date = ''
                """)
            if "reason" in inv_cols:
                _safe_execute("""
                    UPDATE InventoryLog
                    SET notes = COALESCE(NULLIF(notes, ''), reason)
                    WHERE notes IS NULL OR notes = ''
                """)

            _ensure_column("AcademicPeriods", "year_id", "INTEGER")
            _ensure_column("Grades", "year_id", "INTEGER")
            _ensure_column("StudentAttendance", "year_id", "INTEGER")
            _ensure_column("StudentAttendance", "period_id", "INTEGER")
            _ensure_column("StudentAttendance", "recorded_by", "TEXT")
            _ensure_column("StudentDiscipline", "year_id", "INTEGER")
            _ensure_column("StudentDiscipline", "period_id", "INTEGER")
            _ensure_column("StudentDiscipline", "sanction", "TEXT")
            _ensure_column("StudentDiscipline", "points_deducted", "REAL DEFAULT 0")
            _ensure_column("StudentDiscipline", "observation", "TEXT")

            discipline_cols = _table_columns("StudentDiscipline")
            if "action_taken" in discipline_cols:
                _safe_execute("""
                    UPDATE StudentDiscipline
                    SET sanction = COALESCE(NULLIF(sanction, ''), action_taken)
                    WHERE sanction IS NULL OR sanction = ''
                """)
            if "description" in discipline_cols:
                _safe_execute("""
                    UPDATE StudentDiscipline
                    SET observation = COALESCE(NULLIF(observation, ''), description)
                    WHERE observation IS NULL OR observation = ''
                """)
            if "severity_level" in discipline_cols:
                _safe_execute("""
                    UPDATE StudentDiscipline
                    SET points_deducted = CASE
                        WHEN points_deducted IS NULL THEN
                            CASE
                                WHEN LOWER(COALESCE(severity_level, '')) IN ('faible', 'low', 'mineure') THEN 0.5
                                WHEN LOWER(COALESCE(severity_level, '')) IN ('moyenne', 'medium') THEN 1.0
                                WHEN LOWER(COALESCE(severity_level, '')) IN ('grave', 'high', 'severe') THEN 2.0
                                ELSE 0
                            END
                        ELSE points_deducted
                    END
                """)
            _safe_execute("""
                UPDATE StudentDiscipline
                SET points_deducted = COALESCE(points_deducted, 0)
                WHERE points_deducted IS NULL
            """)

            _ensure_column("Payments", "year_id", "INTEGER")
            _ensure_column("StudentDues", "year_id", "INTEGER")
            _ensure_column("StudentDues", "fee_description", "TEXT")
            _ensure_column("MonthlyPaymentsStatus", "due_id", "INTEGER")
            if True:

                        # MonthlyPaymentsStatus legacy support:
                        # بعض الإصدارات كانت تستخدم month_index لتخزين due_id
                        _safe_execute("""
                                UPDATE MonthlyPaymentsStatus
                                SET due_id = month_index
                                WHERE (due_id IS NULL OR due_id = 0)
                                    AND month_index IS NOT NULL
                        """)


            # Core reporting indexes (must be created after all target tables exist)
            reporting_index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_students_class_status ON Students(status)",
                "CREATE INDEX IF NOT EXISTS idx_student_class_numbers_year_student ON StudentClassNumbers(year_id, student_id)",
                "CREATE INDEX IF NOT EXISTS idx_assessment_period ON AssessmentTypes(period_id)",
                "CREATE INDEX IF NOT EXISTS idx_academic_periods_year_cycle_sort ON AcademicPeriods(year_id, cycle_id, sort_order)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_student_year_status ON StudentAttendance(student_id, year_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_year ON StudentAttendance(year_id)",
                "CREATE INDEX IF NOT EXISTS idx_attendance_year_period ON StudentAttendance(year_id, period_id)",
                "CREATE INDEX IF NOT EXISTS idx_discipline_student_year ON StudentDiscipline(student_id, year_id)",
                "CREATE INDEX IF NOT EXISTS idx_discipline_year ON StudentDiscipline(year_id)",
                "CREATE INDEX IF NOT EXISTS idx_discipline_year_period ON StudentDiscipline(year_id, period_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_date ON Payments(transaction_date)",
                "CREATE INDEX IF NOT EXISTS idx_expenses_date ON Expenses(expense_date)",
                "CREATE INDEX IF NOT EXISTS idx_student_dues_student_year ON StudentDues(student_id, year_id)",
                "CREATE INDEX IF NOT EXISTS idx_monthly_payments_due_id ON MonthlyPaymentsStatus(due_id)"
            ]
            for stmt in reporting_index_statements:
                try:
                    cursor.execute(stmt)
                except sqlite3.OperationalError as idx_err:
                    logger.warning(f"Index creation skipped for statement '{stmt}': {idx_err}")

            # --- حفظ التغييرات ---
            conn.commit()
            logger.info("✅ قاعدة البيانات جاهزة ومحدثة (All structures verified).")

# عند تشغيل الملف مباشرة
if __name__ == "__main__":
    db = DatabaseManager()
    db.initialize_database()