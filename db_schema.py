"""Database schema initialization -- extracted from database_setup.py."""
import logging
from psycopg2 import Error  # noqa: F401

_logger = logging.getLogger("DatabaseManager")


def initialize_schema(db_manager) -> None:
    """Create / migrate all database tables. Call once at startup."""
    """إنشاء جميع الجداول المطلوبة للنظام دفعة واحدة"""
    _logger.info("🔄 جاري تهيئة قاعدة البيانات والتحقق من الهيكلة (PostgreSQL)...")

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        def _table_columns(table_name):
            # في PostgreSQL نبحث في information_schema والجداول تحفظ بأحرف صغيرة
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s;",
                (table_name.lower(),),
            )
            return [row[0] for row in cursor.fetchall()]

        def _column_exists(table_name, column_name):
            return column_name.lower() in _table_columns(table_name)

        def _ensure_column(table_name, column_name, column_sql):
            if not _column_exists(table_name, column_name):
                try:
                    cursor.execute("SAVEPOINT sp_ensure_col;")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
                    cursor.execute("RELEASE SAVEPOINT sp_ensure_col;")
                    _logger.info(f"🛠️ Migration: Added missing column {table_name}.{column_name}")
                except Exception as e:
                    cursor.execute("ROLLBACK TO SAVEPOINT sp_ensure_col;")
                    _logger.error(f"Migration failed for {table_name}.{column_name}: {e}")

        def _safe_execute(sql, params=()):
            try:
                # استخدام SAVEPOINT لحماية الترانزاكشن الرئيسي من الانهيار عند حدوث خطأ
                cursor.execute("SAVEPOINT sp_safe_execute;")
                cursor.execute(sql, params)
                cursor.execute("RELEASE SAVEPOINT sp_safe_execute;")
            except Error as err:
                cursor.execute("ROLLBACK TO SAVEPOINT sp_safe_execute;")
                _logger.warning(f"Migration statement skipped -> {err}")

        # --- 1. System & Users ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                id SERIAL PRIMARY KEY,
                staff_id INTEGER,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'User',
                status TEXT DEFAULT 'Actif',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS AuditLogs (
                id SERIAL PRIMARY KEY,
                actor TEXT,
                action TEXT,
                target TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS EmailSettings (
                id SERIAL PRIMARY KEY,
                smtp_server TEXT,
                smtp_port TEXT,
                email_address TEXT,
                email_password TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS NotificationLogs (
                id SERIAL PRIMARY KEY,
                recipient_type TEXT,
                recipient_contact TEXT,
                subject TEXT,
                status TEXT,
                error_msg TEXT,
                sent_at TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS SchoolInfo (
                id SERIAL PRIMARY KEY,
                republic TEXT, ia TEXT, ief TEXT, school_name TEXT,
                auth_number TEXT, address TEXT, phone TEXT, logo_path TEXT, director_name TEXT
            )
        """
        )

        # --- 2. Academic Structure ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS AcademicYears (
                id SERIAL PRIMARY KEY,
                year_label TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 0
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Cycles (
                id SERIAL PRIMARY KEY,
                name_ar TEXT,
                name_fr TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Classes (
                id SERIAL PRIMARY KEY,
                cycle_id INTEGER,
                class_name_ar TEXT,
                class_name_fr TEXT,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (cycle_id) REFERENCES Cycles(id) ON DELETE CASCADE
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS AcademicPeriods (
                id SERIAL PRIMARY KEY,
                year_id INTEGER,
                cycle_id INTEGER,
                period_name_ar TEXT,
                period_name_fr TEXT,
                sort_order INTEGER,
                FOREIGN KEY (year_id) REFERENCES AcademicYears(id),
                FOREIGN KEY (cycle_id) REFERENCES Cycles(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Subjects (
                id SERIAL PRIMARY KEY,
                cycle_id INTEGER,
                subject_name_ar TEXT,
                subject_name_fr TEXT,
                coefficient REAL DEFAULT 1,
                subject_lang TEXT DEFAULT 'Français',
                FOREIGN KEY (cycle_id) REFERENCES Cycles(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS AssessmentTypes (
                id SERIAL PRIMARY KEY,
                period_id INTEGER,
                name_ar TEXT,
                name_fr TEXT,
                type_code TEXT,
                weight_percentage REAL DEFAULT 1.0,
                FOREIGN KEY (period_id) REFERENCES AcademicPeriods(id)
            )
        """
        )

        # --- 3. People (Students & Staff) ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Students (
                id SERIAL PRIMARY KEY,
                first_name_fr TEXT NOT NULL, last_name_fr TEXT NOT NULL,
                first_name_ar TEXT NOT NULL, last_name_ar TEXT NOT NULL,
                birth_date DATE, birth_place TEXT,
                gender TEXT,
                address TEXT,
                parent_name TEXT, parent_phone TEXT, parent_email TEXT, parent_address TEXT,
                registration_date DATE DEFAULT CURRENT_DATE,
                status TEXT DEFAULT 'Active',
                photo_path TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS StudentClassNumbers (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                class_id INTEGER,
                year_id INTEGER,
                class_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES Students (id) ON DELETE CASCADE,
                FOREIGN KEY (class_id) REFERENCES Classes (id),
                FOREIGN KEY (year_id) REFERENCES AcademicYears (id),
                UNIQUE (student_id, year_id),
                UNIQUE (class_id, year_id, class_number)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Staff (
                id SERIAL PRIMARY KEY,
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
        """
        )

        # إضافة الـ Foreign Key الخاص بجدول Users بعد إنشاء Staff
        _safe_execute(
            """
            ALTER TABLE Users
            ADD CONSTRAINT fk_staff
            FOREIGN KEY (staff_id) REFERENCES Staff(id) ON DELETE SET NULL;
        """
        )

        # --- 4. Academic Data (Grades, Attendance, Discipline) ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Grades (
                id SERIAL PRIMARY KEY,
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
        """
        )

        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_grades_student_subject ON Grades(student_id, subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_grades_assessment ON Grades(assessment_id)",
            "CREATE INDEX IF NOT EXISTS idx_grades_date ON Grades(date_recorded)",
            "CREATE INDEX IF NOT EXISTS idx_grades_year ON Grades(year_id)",
        ]
        for stmt in index_statements:
            cursor.execute(stmt)

        cursor.execute(
            """
           CREATE TABLE IF NOT EXISTS StudentAttendance (
                id SERIAL PRIMARY KEY,
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
        """
        )

        cursor.execute(
            """
           CREATE TABLE IF NOT EXISTS StaffAttendance (
                id SERIAL PRIMARY KEY,
                staff_id INTEGER,
                attendance_date TEXT,
                check_in_time TEXT,
                check_out_time TEXT,
                status TEXT,
                note TEXT,
                FOREIGN KEY (staff_id) REFERENCES Staff(id)
           )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS StaffLeaves (
                id SERIAL PRIMARY KEY,
                staff_id INTEGER,
                leave_type TEXT,
                start_date DATE,
                end_date DATE,
                days_count INTEGER,
                reason TEXT,
                status TEXT DEFAULT 'En Attente',
                FOREIGN KEY(staff_id) REFERENCES Staff(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS StudentDiscipline (
                id SERIAL PRIMARY KEY,
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
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Timetable (
                id SERIAL PRIMARY KEY,
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
        """
        )

        # --- 5. Finance ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS RegistrationFees (
                id SERIAL PRIMARY KEY,
                class_id INTEGER,
                amount REAL,
                FOREIGN KEY (class_id) REFERENCES Classes(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS MonthlyFeeSchedule (
                id SERIAL PRIMARY KEY,
                class_id INTEGER,
                month_index INTEGER,
                month_name TEXT,
                amount REAL,
                FOREIGN KEY (class_id) REFERENCES Classes(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Payments (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                year_id INTEGER,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_due REAL,
                discount REAL DEFAULT 0,
                amount_paid REAL,
                remaining_balance REAL,
                payment_type TEXT,
                details TEXT,
                FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE RESTRICT,
                FOREIGN KEY (year_id) REFERENCES AcademicYears(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS StudentDues (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                year_id INTEGER,
                fee_type TEXT,
                fee_description TEXT,
                original_amount REAL,
                discount_amount REAL DEFAULT 0,
                net_amount REAL,
                due_date DATE,
                is_paid INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES Students(id),
                FOREIGN KEY (year_id) REFERENCES AcademicYears(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS MonthlyPaymentsStatus (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                month_index INTEGER,
                due_id INTEGER,
                payment_id INTEGER,
                amount_paid REAL,
                FOREIGN KEY (student_id) REFERENCES Students(id),
                FOREIGN KEY (due_id) REFERENCES StudentDues(id),
                FOREIGN KEY (payment_id) REFERENCES Payments(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Expenses (
                id SERIAL PRIMARY KEY,
                category TEXT,
                amount REAL,
                description TEXT,
                expense_date DATE,
                paid_to TEXT,
                created_at TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS SalarySlips (
                id SERIAL PRIMARY KEY,
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
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS InventoryItems (
                id SERIAL PRIMARY KEY,
                name_fr TEXT,
                name_ar TEXT,
                category TEXT,
                quantity INTEGER DEFAULT 0,
                min_quantity INTEGER DEFAULT 5,
                unit_price REAL DEFAULT 0.0,
                location TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS InventoryLog (
                id SERIAL PRIMARY KEY,
                item_id INTEGER,
                transaction_type TEXT,
                quantity INTEGER,
                transaction_date TEXT,
                notes TEXT,
                performed_by TEXT,
                expense_id INTEGER,
                FOREIGN KEY (item_id) REFERENCES InventoryItems(id)
            )
        """
        )

        # --- 5.b Schema Migrations (backward compatibility) ---
        _ensure_column("AcademicYears", "year_label", "TEXT")
        academic_year_cols = _table_columns("AcademicYears")
        if "year_name" in academic_year_cols:
            _safe_execute(
                """
                UPDATE AcademicYears
                SET year_label = COALESCE(NULLIF(year_label, ''), year_name)
                WHERE year_label IS NULL OR year_label = ''
            """
            )
        if "start_date" in academic_year_cols and "end_date" in academic_year_cols:
            # استخدام PostgreSQL Syntax للتاريخ TO_CHAR بدلاً من strftime
            _safe_execute(
                """
                UPDATE AcademicYears
                SET year_label = COALESCE(
                    NULLIF(year_label, ''),
                    TO_CHAR(CAST(start_date AS DATE), 'YYYY') || '-' || TO_CHAR(CAST(end_date AS DATE), 'YYYY')
                )
                WHERE year_label IS NULL OR year_label = ''
            """
            )

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
            _safe_execute(
                """
                UPDATE Staff
                SET first_name = COALESCE(NULLIF(first_name, ''), staff_name)
                WHERE first_name IS NULL OR first_name = ''
            """
            )
        _safe_execute(
            """
            UPDATE Staff
            SET last_name = COALESCE(NULLIF(last_name, ''), '')
            WHERE last_name IS NULL
        """
        )
        if "position" in staff_cols:
            _safe_execute(
                """
                UPDATE Staff
                SET role = COALESCE(NULLIF(role, ''), position)
                WHERE role IS NULL OR role = ''
            """
            )
        if "salary" in staff_cols:
            _safe_execute(
                """
                UPDATE Staff
                SET salary_base = COALESCE(salary_base, salary)
                WHERE salary_base IS NULL OR salary_base = 0
            """
            )

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
            _safe_execute(
                """
                UPDATE Students
                SET first_name_fr = COALESCE(NULLIF(first_name_fr, ''), student_name)
                WHERE first_name_fr IS NULL OR first_name_fr = ''
            """
            )
        _safe_execute(
            """
            UPDATE Students
            SET first_name_fr = COALESCE(NULLIF(first_name_fr, ''), 'Élève')
            WHERE first_name_fr IS NULL OR first_name_fr = ''
        """
        )
        _safe_execute(
            """
            UPDATE Students
            SET last_name_fr = COALESCE(last_name_fr, '')
            WHERE last_name_fr IS NULL
        """
        )
        _safe_execute(
            """
            UPDATE Students
            SET first_name_ar = COALESCE(first_name_ar, '')
            WHERE first_name_ar IS NULL
        """
        )
        _safe_execute(
            """
            UPDATE Students
            SET last_name_ar = COALESCE(last_name_ar, '')
            WHERE last_name_ar IS NULL
        """
        )

        _ensure_column("RegistrationFees", "class_id", "INTEGER")
        _ensure_column("MonthlyFeeSchedule", "class_id", "INTEGER")
        _ensure_column("MonthlyFeeSchedule", "month_name", "TEXT")

        reg_cols = _table_columns("RegistrationFees")
        if "cycle_id" in reg_cols:
            _safe_execute(
                """
                UPDATE RegistrationFees
                SET class_id = (
                    SELECT id FROM Classes c
                    WHERE c.cycle_id = RegistrationFees.cycle_id
                    ORDER BY c.sort_order, c.id
                    LIMIT 1
                )
                WHERE (class_id IS NULL OR class_id = 0) AND cycle_id IS NOT NULL
            """
            )

        mfs_cols = _table_columns("MonthlyFeeSchedule")
        if "cycle_id" in mfs_cols:
            _safe_execute(
                """
                UPDATE MonthlyFeeSchedule
                SET class_id = (
                    SELECT id FROM Classes c
                    WHERE c.cycle_id = MonthlyFeeSchedule.cycle_id
                    ORDER BY c.sort_order, c.id
                    LIMIT 1
                )
                WHERE (class_id IS NULL OR class_id = 0) AND cycle_id IS NOT NULL
            """
            )
        _safe_execute(
            """
            UPDATE MonthlyFeeSchedule
            SET month_name = COALESCE(NULLIF(month_name, ''), 'Mois ' || month_index)
            WHERE month_name IS NULL OR month_name = ''
        """
        )

        _ensure_column("StaffAttendance", "attendance_date", "TEXT")
        _ensure_column("StaffAttendance", "check_in_time", "TEXT")
        _ensure_column("StaffAttendance", "check_out_time", "TEXT")
        _ensure_column("StaffAttendance", "status", "TEXT")
        _ensure_column("StaffAttendance", "note", "TEXT")
        staff_att_cols = _table_columns("StaffAttendance")
        if "date" in staff_att_cols:
            _safe_execute(
                """
                UPDATE StaffAttendance
                SET attendance_date = COALESCE(NULLIF(attendance_date, ''), date)
                WHERE attendance_date IS NULL OR attendance_date = ''
            """
            )
        if "notes" in staff_att_cols:
            _safe_execute(
                """
                UPDATE StaffAttendance
                SET note = COALESCE(NULLIF(note, ''), notes)
                WHERE note IS NULL OR note = ''
            """
            )

        _ensure_column("InventoryLog", "transaction_type", "TEXT")
        _ensure_column("InventoryLog", "quantity", "INTEGER")
        _ensure_column("InventoryLog", "transaction_date", "TEXT")
        _ensure_column("InventoryLog", "notes", "TEXT")
        inv_cols = _table_columns("InventoryLog")
        if "trasaction_type" in inv_cols:
            _safe_execute(
                """
                UPDATE InventoryLog
                SET transaction_type = COALESCE(NULLIF(transaction_type, ''), trasaction_type)
                WHERE transaction_type IS NULL OR transaction_type = ''
            """
            )
        if "action" in inv_cols:
            _safe_execute(
                """
                UPDATE InventoryLog
                SET transaction_type = COALESCE(NULLIF(transaction_type, ''), action)
                WHERE transaction_type IS NULL OR transaction_type = ''
            """
            )
        if "quantity_change" in inv_cols:
            _safe_execute(
                """
                UPDATE InventoryLog
                SET quantity = COALESCE(quantity, quantity_change)
                WHERE quantity IS NULL
            """
            )
        if "date_time" in inv_cols:
            _safe_execute(
                """
                UPDATE InventoryLog
                SET transaction_date = COALESCE(NULLIF(transaction_date, ''), date_time)
                WHERE transaction_date IS NULL OR transaction_date = ''
            """
            )
        if "reason" in inv_cols:
            _safe_execute(
                """
                UPDATE InventoryLog
                SET notes = COALESCE(NULLIF(notes, ''), reason)
                WHERE notes IS NULL OR notes = ''
            """
            )

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
            _safe_execute(
                """
                UPDATE StudentDiscipline
                SET sanction = COALESCE(NULLIF(sanction, ''), action_taken)
                WHERE sanction IS NULL OR sanction = ''
            """
            )
        if "description" in discipline_cols:
            _safe_execute(
                """
                UPDATE StudentDiscipline
                SET observation = COALESCE(NULLIF(observation, ''), description)
                WHERE observation IS NULL OR observation = ''
            """
            )
        if "severity_level" in discipline_cols:
            _safe_execute(
                """
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
            """
            )
        _safe_execute(
            """
            UPDATE StudentDiscipline
            SET points_deducted = COALESCE(points_deducted, 0)
            WHERE points_deducted IS NULL
        """
        )

        _ensure_column("Payments", "year_id", "INTEGER")
        _ensure_column("StudentDues", "year_id", "INTEGER")
        _ensure_column("StudentDues", "fee_description", "TEXT")
        _ensure_column("MonthlyPaymentsStatus", "due_id", "INTEGER")

        _safe_execute(
            """
            UPDATE MonthlyPaymentsStatus
            SET due_id = month_index
            WHERE (due_id IS NULL OR due_id = 0)
                AND month_index IS NOT NULL
        """
        )

        # Core reporting indexes
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
            "CREATE INDEX IF NOT EXISTS idx_monthly_payments_due_id ON MonthlyPaymentsStatus(due_id)",
        ]
        for stmt in reporting_index_statements:
            try:
                cursor.execute("SAVEPOINT sp_index;")
                cursor.execute(stmt)
                cursor.execute("RELEASE SAVEPOINT sp_index;")
            except Error as idx_err:
                cursor.execute("ROLLBACK TO SAVEPOINT sp_index;")
                _logger.warning(f"Index creation skipped for statement '{stmt}': {idx_err}")

        # ─────────────────────────────────────────────────────────────
        # Phase 5.2 — عمود parent_pin لبوابة أولياء الأمور
        # Phase 5.4 — دعم متعدد المدارس (Schema)
        # Phase 6.3 — رمز ثابت وفريد للطالب (student_code) + تشفير PIN
        # ─────────────────────────────────────────────────────────────
        _ensure_column("Students", "parent_pin", "TEXT DEFAULT NULL")

        # student_code: معرّف ثابت وفريد للطالب يُستعمل في بوابة الأولياء
        # الصيغة: EMG-XXXX — لا يتغير عبر السنوات ولا يتأثر بتغيير الفصل
        _ensure_column("Students", "student_code", "TEXT DEFAULT NULL")
        _safe_execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_code ON Students(student_code) WHERE student_code IS NOT NULL"
        )
        # توليد student_code تلقائيًا للطلاب الموجودين الذين لا يملكون كودًا
        cursor.execute("SELECT id FROM Students WHERE student_code IS NULL ORDER BY id")
        students_without_code = cursor.fetchall()
        for (sid,) in students_without_code:
            code = f"EMG-{sid:04d}"
            cursor.execute(
                "UPDATE Students SET student_code = %s WHERE id = %s AND student_code IS NULL", (code, sid)
            )
        if students_without_code:
            _logger.info(f"🔑 Migration: student_code généré pour {len(students_without_code)} élève(s).")

        # parent_pin_hash: عمود منفصل للـ PIN المشفر (يحل محل parent_pin النصي تدريجيًا)
        # المنطق: إذا parent_pin_hash موجود → استخدمه؛ إذا لا → يستخدم parent_pin القديم + ترقية تلقائية
        _ensure_column("Students", "parent_pin_hash", "TEXT DEFAULT NULL")

        # جدول المدارس المرجعي (للاستخدام الحالي والمستقبلي)
        _safe_execute(
            """
            CREATE TABLE IF NOT EXISTS Schools (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                code TEXT UNIQUE,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        _safe_execute(
            "INSERT INTO Schools (id, name, code, is_active) VALUES (1, 'École Principale', 'MAIN', 1) ON CONFLICT (id) DO NOTHING"
        )

        _ensure_column("Students", "school_id", "INTEGER DEFAULT 1")
        _ensure_column("Staff", "school_id", "INTEGER DEFAULT 1")
        _ensure_column("Classes", "school_id", "INTEGER DEFAULT 1")
        _ensure_column("AcademicYears", "school_id", "INTEGER DEFAULT 1")

        # توحيد البيانات الحالية على المدرسة الافتراضية
        _safe_execute("UPDATE Students SET school_id = 1 WHERE school_id IS NULL")
        _safe_execute("UPDATE Staff SET school_id = 1 WHERE school_id IS NULL")
        _safe_execute("UPDATE Classes SET school_id = 1 WHERE school_id IS NULL")
        _safe_execute("UPDATE AcademicYears SET school_id = 1 WHERE school_id IS NULL")

        # فهارس للأداء
        _safe_execute("CREATE INDEX IF NOT EXISTS idx_students_school ON Students(school_id)")
        _safe_execute("CREATE INDEX IF NOT EXISTS idx_staff_school ON Staff(school_id)")
        _safe_execute("CREATE INDEX IF NOT EXISTS idx_classes_school ON Classes(school_id)")
        _safe_execute("CREATE INDEX IF NOT EXISTS idx_years_school ON AcademicYears(school_id)")
        _safe_execute(
            "CREATE INDEX IF NOT EXISTS idx_students_parent_pin ON Students(parent_pin) WHERE parent_pin IS NOT NULL"
        )

        # --- حفظ التغييرات ---
        conn.commit()
        _logger.info("✅ قاعدة البيانات جاهزة ومحدثة (PostgreSQL Structures verified).")


# عند تشغيل الملف مباشرة

# ─────────────────────────────────────────────────────────────────────────────
# Audit Log Helper
# ─────────────────────────────────────────────────────────────────────────────
