"""Initial schema — all tables for El Malick Gest

Revision ID: 001
Revises:
Create Date: 2026-05-15

هذا migration يوثق الهيكل الكامل لقاعدة البيانات.
آمن للتشغيل على قاعدة بيانات موجودة (IF NOT EXISTS في كل مكان).
"""

from alembic import op

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # 1. System & Users
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
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

    op.execute(
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

    op.execute(
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

    op.execute(
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

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS SchoolInfo (
            id SERIAL PRIMARY KEY,
            republic TEXT,
            ia TEXT,
            ief TEXT,
            school_name TEXT,
            auth_number TEXT,
            address TEXT,
            phone TEXT,
            logo_path TEXT,
            director_name TEXT
        )
        """
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Academic Structure
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS AcademicYears (
            id SERIAL PRIMARY KEY,
            year_label TEXT UNIQUE NOT NULL,
            is_active INTEGER DEFAULT 0,
            school_id INTEGER DEFAULT 1
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS Cycles (
            id SERIAL PRIMARY KEY,
            name_ar TEXT,
            name_fr TEXT
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS Classes (
            id SERIAL PRIMARY KEY,
            cycle_id INTEGER,
            class_name_ar TEXT,
            class_name_fr TEXT,
            sort_order INTEGER DEFAULT 0,
            school_id INTEGER DEFAULT 1,
            FOREIGN KEY (cycle_id) REFERENCES Cycles(id) ON DELETE CASCADE
        )
        """
    )

    op.execute(
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

    op.execute(
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

    op.execute(
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

    # ─────────────────────────────────────────────────────────────────────────
    # 3. People — Students & Staff
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS Students (
            id SERIAL PRIMARY KEY,
            first_name_fr TEXT NOT NULL,
            last_name_fr TEXT NOT NULL,
            first_name_ar TEXT NOT NULL,
            last_name_ar TEXT NOT NULL,
            birth_date DATE,
            birth_place TEXT,
            gender TEXT,
            address TEXT,
            parent_name TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            parent_address TEXT,
            registration_date DATE DEFAULT CURRENT_DATE,
            status TEXT DEFAULT 'Active',
            photo_path TEXT,
            parent_pin TEXT DEFAULT NULL,
            student_code TEXT DEFAULT NULL,
            parent_pin_hash TEXT DEFAULT NULL,
            school_id INTEGER DEFAULT 1
        )
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_code "
        "ON Students(student_code) WHERE student_code IS NOT NULL"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS StudentClassNumbers (
            id SERIAL PRIMARY KEY,
            student_id INTEGER,
            class_id INTEGER,
            year_id INTEGER,
            class_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE CASCADE,
            FOREIGN KEY (class_id) REFERENCES Classes(id),
            FOREIGN KEY (year_id) REFERENCES AcademicYears(id),
            UNIQUE (student_id, year_id),
            UNIQUE (class_id, year_id, class_number)
        )
        """
    )

    op.execute(
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
            status TEXT DEFAULT 'Actif',
            school_id INTEGER DEFAULT 1
        )
        """
    )

    # FK: Users → Staff (ajouté après création de Staff)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_staff'
            ) THEN
                ALTER TABLE Users
                ADD CONSTRAINT fk_staff
                FOREIGN KEY (staff_id) REFERENCES Staff(id) ON DELETE SET NULL;
            END IF;
        END
        $$
        """
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Academic Data — Grades, Attendance, Discipline
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
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
            FOREIGN KEY (student_id) REFERENCES Students(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES Subjects(id),
            FOREIGN KEY (assessment_id) REFERENCES AssessmentTypes(id),
            FOREIGN KEY (year_id) REFERENCES AcademicYears(id)
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_grades_student_subject ON Grades(student_id, subject_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_grades_assessment ON Grades(assessment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_grades_date ON Grades(date_recorded)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_grades_year ON Grades(year_id)")

    op.execute(
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

    op.execute(
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

    op.execute(
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
            FOREIGN KEY (staff_id) REFERENCES Staff(id)
        )
        """
    )

    op.execute(
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

    op.execute(
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

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Finance
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS RegistrationFees (
            id SERIAL PRIMARY KEY,
            class_id INTEGER,
            amount REAL,
            FOREIGN KEY (class_id) REFERENCES Classes(id)
        )
        """
    )

    op.execute(
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

    op.execute(
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

    op.execute(
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

    op.execute(
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

    op.execute(
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

    op.execute(
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

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Inventory
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
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

    op.execute(
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

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Schools (multi-school support)
    # ─────────────────────────────────────────────────────────────────────────
    op.execute(
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

    op.execute(
        "INSERT INTO Schools (id, name, code, is_active) "
        "VALUES (1, 'École Principale', 'MAIN', 1) ON CONFLICT (id) DO NOTHING"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Performance Indexes
    # ─────────────────────────────────────────────────────────────────────────
    indexes = [
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
    for stmt in indexes:
        op.execute(stmt)


def downgrade() -> None:
    """
    Downgrade حذر — يحذف الجداول بالترتيب العكسي لتجنب أخطاء FK.
    تحذير: هذا يحذف جميع البيانات. استخدم فقط في بيئة التطوير.
    """
    tables_in_reverse = [
        "MonthlyPaymentsStatus",
        "StudentDues",
        "Payments",
        "MonthlyFeeSchedule",
        "RegistrationFees",
        "SalarySlips",
        "Expenses",
        "InventoryLog",
        "InventoryItems",
        "Timetable",
        "StudentDiscipline",
        "StaffLeaves",
        "StaffAttendance",
        "StudentAttendance",
        "Grades",
        "Staff",
        "StudentClassNumbers",
        "Students",
        "AssessmentTypes",
        "Subjects",
        "AcademicPeriods",
        "Classes",
        "Cycles",
        "AcademicYears",
        "Schools",
        "SchoolInfo",
        "NotificationLogs",
        "EmailSettings",
        "AuditLogs",
        "Users",
    ]
    for table in tables_in_reverse:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
