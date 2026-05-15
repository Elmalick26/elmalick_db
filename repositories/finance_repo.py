"""Finance repository — payment and dues data access for El Malick Gest."""

from __future__ import annotations


class FinanceRepository:
    """Data access for finance-related queries (dues, payments, history)."""

    def __init__(self, conn):
        self.conn = conn

    # ──────────────────────────────────────────────
    # Classes & Students (finance context)
    # ──────────────────────────────────────────────

    def list_classes(self) -> list[tuple]:
        """Return (id, class_name_fr) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, class_name_fr FROM Classes ORDER BY class_name_fr")
        return cursor.fetchall()

    def list_students_by_class(self, class_id: int, year_id: int) -> list[tuple]:
        """Return (id, full_name_fr) for active students in a class/year."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id, TRIM(COALESCE(S.first_name_fr, '') || ' ' || COALESCE(S.last_name_fr, ''))
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id = %s AND SCN.year_id = %s AND S.status = 'Active'
            ORDER BY S.last_name_fr, S.first_name_fr
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    # ──────────────────────────────────────────────
    # Dues
    # ──────────────────────────────────────────────

    def list_dues_for_student(self, student_id: int, year_id: int) -> list[tuple]:
        """Return dues for a student with already-paid totals.

        Columns: (id, fee_description, net_amount, is_paid, due_date, total_paid)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT D.id, D.fee_description, D.net_amount, D.is_paid, D.due_date,
                   COALESCE((
                       SELECT SUM(amount_paid)
                       FROM MonthlyPaymentsStatus
                       WHERE due_id = D.id OR (due_id IS NULL AND month_index = D.id)
                   ), 0) AS total_paid
            FROM StudentDues D
            WHERE D.student_id = %s AND D.year_id = %s
            ORDER BY D.due_date ASC, D.id ASC
            """,
            (student_id, year_id),
        )
        return cursor.fetchall()

    # ──────────────────────────────────────────────
    # Late payers
    # ──────────────────────────────────────────────

    def list_late_payers(self, year_id: int, as_of_date: str) -> list[tuple]:
        """Return (full_name, class_name, invoice_list, total_debt) for overdue active students."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TRIM(COALESCE(S.first_name_fr, '') || ' ' || COALESCE(S.last_name_fr, '')),
                   C.class_name_fr,
                   STRING_AGG(COALESCE(D.fee_description, D.fee_type), ', '),
                   SUM(
                       CASE
                           WHEN (D.net_amount - COALESCE((
                               SELECT SUM(MPS.amount_paid)
                               FROM MonthlyPaymentsStatus MPS
                               WHERE MPS.due_id = D.id OR (MPS.due_id IS NULL AND MPS.month_index = D.id)
                           ), 0)) > 0
                           THEN (D.net_amount - COALESCE((
                               SELECT SUM(MPS2.amount_paid)
                               FROM MonthlyPaymentsStatus MPS2
                               WHERE MPS2.due_id = D.id OR (MPS2.due_id IS NULL AND MPS2.month_index = D.id)
                           ), 0))
                           ELSE 0
                       END
                   )
            FROM StudentDues D
            JOIN Students S ON D.student_id = S.id
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = D.year_id
            JOIN Classes C ON SCN.class_id = C.id
            WHERE D.year_id = %s AND D.is_paid = 0 AND D.due_date <= %s AND S.status = 'Active'
            GROUP BY S.id, C.class_name_fr
            HAVING SUM(
                CASE
                    WHEN (D.net_amount - COALESCE((
                        SELECT SUM(MPS3.amount_paid)
                        FROM MonthlyPaymentsStatus MPS3
                        WHERE MPS3.due_id = D.id OR (MPS3.due_id IS NULL AND MPS3.month_index = D.id)
                    ), 0)) > 0
                    THEN (D.net_amount - COALESCE((
                        SELECT SUM(MPS4.amount_paid)
                        FROM MonthlyPaymentsStatus MPS4
                        WHERE MPS4.due_id = D.id OR (MPS4.due_id IS NULL AND MPS4.month_index = D.id)
                    ), 0))
                    ELSE 0
                END
            ) > 0
            ORDER BY S.last_name_fr, S.first_name_fr
            """,
            (year_id, as_of_date),
        )
        return cursor.fetchall()

    # ──────────────────────────────────────────────
    # Payments
    # ──────────────────────────────────────────────

    def record_payment(
        self,
        student_id: int,
        year_id: int,
        transaction_date: str,
        total_due: float,
        amount_received: float,
        description: str,
        allocations: list[dict],
    ) -> int:
        """Insert a payment record and distribute amount across dues.

        Each allocation dict: {"id": due_id, "amount_due": remaining_amount}
        Returns the new payment id.
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO Payments (
                student_id, year_id, transaction_date, total_due,
                discount, amount_paid, remaining_balance, payment_type, details
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                student_id,
                year_id,
                transaction_date,
                total_due,
                0,
                amount_received,
                max(0.0, total_due - amount_received),
                "Invoice Payment",
                description,
            ),
        )
        payment_id = cursor.fetchone()[0]

        amount_remaining = amount_received
        for due in allocations:
            if amount_remaining <= 0:
                break
            due_id = due["id"]
            amount_for_due = min(due["amount_due"], amount_remaining)

            cursor.execute(
                """
                INSERT INTO MonthlyPaymentsStatus (student_id, month_index, due_id, payment_id, amount_paid)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (student_id, due_id, due_id, payment_id, amount_for_due),
            )
            amount_remaining -= amount_for_due

            cursor.execute(
                """
                SELECT net_amount,
                       COALESCE((
                           SELECT SUM(amount_paid)
                           FROM MonthlyPaymentsStatus
                           WHERE due_id = %s OR (due_id IS NULL AND month_index = %s)
                       ), 0) AS total_paid
                FROM StudentDues WHERE id = %s
                """,
                (due_id, due_id, due_id),
            )
            due_status = cursor.fetchone()
            if due_status and due_status[1] >= due_status[0]:
                cursor.execute("UPDATE StudentDues SET is_paid=1 WHERE id=%s", (due_id,))

        return payment_id

    def list_payment_history(self, student_id: int) -> list[tuple]:
        """Return (id, transaction_date, details, total_due, amount_paid) ordered newest first."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, transaction_date, details, total_due, amount_paid
            FROM Payments
            WHERE student_id = %s
            ORDER BY id DESC
            """,
            (student_id,),
        )
        return cursor.fetchall()

    def get_payment_receipt_data(self, payment_id: int) -> tuple | None:
        """Return full payment data for receipt generation.

        Columns:
          (id, transaction_date, student_full_name, class_name_fr,
           total_due, discount, amount_paid, remaining_balance, details)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT P.id, P.transaction_date,
                   S.first_name_fr || ' ' || S.last_name_fr,
                   C.class_name_fr,
                   P.total_due, P.discount, P.amount_paid, P.remaining_balance, P.details
            FROM Payments P
            JOIN Students S ON P.student_id = S.id
            LEFT JOIN StudentClassNumbers SCN ON S.id = SCN.student_id AND SCN.year_id = P.year_id
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE P.id = %s
            """,
            (payment_id,),
        )
        return cursor.fetchone()

    # ──────────────────────────────────────────────
    # Academic Year helpers
    # ──────────────────────────────────────────────

    def get_active_year_id(self) -> int:
        """Return the active academic year id, or -1 if none found."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active = 1 LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("SELECT id FROM AcademicYears ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else -1

    # ──────────────────────────────────────────────
    # StudentDues management
    # ──────────────────────────────────────────────

    def get_dues_for_management(self, student_id: int, year_id: int) -> list[tuple]:
        """Return all dues for a student (management view — includes discount columns).

        Columns: (id, fee_type, fee_description, original_amount, discount_amount, net_amount, due_date, is_paid)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, fee_type, fee_description, original_amount, discount_amount, net_amount, due_date, is_paid
            FROM StudentDues
            WHERE student_id = %s AND year_id = %s
            ORDER BY due_date ASC, id ASC
            """,
            (student_id, year_id),
        )
        return cursor.fetchall()

    def add_due(
        self,
        student_id: int,
        year_id: int,
        fee_type: str,
        fee_description: str,
        original_amount: float,
        net_amount: float,
        due_date: str,
    ) -> None:
        """Insert a new StudentDue record."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO StudentDues (student_id, year_id, fee_type, fee_description, original_amount, net_amount, due_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (student_id, year_id, fee_type, fee_description, original_amount, net_amount, due_date),
        )

    def get_due_is_paid(self, due_id: int) -> bool:
        """Return True if the due is already marked as paid."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_paid FROM StudentDues WHERE id = %s", (due_id,))
        row = cursor.fetchone()
        return bool(row and row[0])

    def update_due_discount(self, due_id: int, discount_amount: float, net_amount: float) -> None:
        """Apply a discount to an unpaid due."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE StudentDues SET discount_amount = %s, net_amount = %s WHERE id = %s",
            (discount_amount, net_amount, due_id),
        )

    def delete_due(self, due_id: int) -> None:
        """Delete a StudentDue record."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM StudentDues WHERE id = %s", (due_id,))

    def count_dues_by_type(self, student_id: int, year_id: int, fee_type: str) -> int:
        """Return the number of dues for a student/year/type combination."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM StudentDues WHERE student_id = %s AND year_id = %s AND fee_type = %s",
            (student_id, year_id, fee_type),
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_dues_for_export(self, student_id: int, year_id: int) -> list[tuple]:
        """Return dues for PDF export.

        Columns: (fee_type, fee_description, due_date, original_amount, discount_amount, net_amount, is_paid)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT fee_type, fee_description, due_date, original_amount, discount_amount, net_amount, is_paid
            FROM StudentDues
            WHERE student_id = %s AND year_id = %s
            ORDER BY due_date ASC, id ASC
            """,
            (student_id, year_id),
        )
        return cursor.fetchall()

    def get_student_meta_for_dues(self, student_id: int, year_id: int) -> tuple | None:
        """Return (full_name_fr, class_name_fr, year_label) for PDF header."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TRIM(COALESCE(S.first_name_fr, '') || ' ' || COALESCE(S.last_name_fr, '')),
                   COALESCE(C.class_name_fr, '-'),
                   COALESCE((SELECT year_label FROM AcademicYears WHERE id = %s), '-')
            FROM Students S
            LEFT JOIN StudentClassNumbers SCN ON SCN.student_id = S.id AND SCN.year_id = %s
            LEFT JOIN Classes C ON C.id = SCN.class_id
            WHERE S.id = %s
            LIMIT 1
            """,
            (year_id, year_id, student_id),
        )
        return cursor.fetchone()

    # ──────────────────────────────────────────────
    # Fee schedule (auto-generation)
    # ──────────────────────────────────────────────

    def get_registration_fee(self, class_id: int) -> float:
        """Return the registration fee amount for a class, or 0.0 if not set."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT amount FROM RegistrationFees WHERE class_id = %s", (class_id,))
        row = cursor.fetchone()
        return float(row[0]) if row else 0.0

    def get_monthly_fee_schedule(self, class_id: int) -> list[tuple]:
        """Return (month_index, month_name, amount) ordered by month_index."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT month_index, month_name, amount FROM MonthlyFeeSchedule WHERE class_id = %s ORDER BY month_index",
            (class_id,),
        )
        return cursor.fetchall()

    def list_students_in_class(self, class_id: int, year_id: int) -> list[tuple]:
        """Return (id,) for active students in a class/year (for auto-generation)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.id
            FROM Students S
            JOIN StudentClassNumbers SCN ON S.id = SCN.student_id
            WHERE SCN.class_id = %s AND SCN.year_id = %s AND S.status = 'Active'
            """,
            (class_id, year_id),
        )
        return cursor.fetchall()

    # ──────────────────────────────────────────────
    # Finance dashboard aggregates
    # ──────────────────────────────────────────────

    def get_total_income(self) -> float:
        """Return total sum of all payments."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(amount_paid) FROM Payments")
        row = cursor.fetchone()
        try:
            return float(row[0]) if row and row[0] is not None else 0.0
        except Exception:
            return 0.0

    def get_total_expenses(self) -> float:
        """Return total sum of all expenses."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM Expenses")
        row = cursor.fetchone()
        try:
            return float(row[0]) if row and row[0] is not None else 0.0
        except Exception:
            return 0.0

    def get_total_inventory_value(self) -> float:
        """Return total value of inventory (quantity * unit_price)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(quantity * unit_price) FROM InventoryItems")
        row = cursor.fetchone()
        try:
            return float(row[0]) if row and row[0] is not None else 0.0
        except Exception:
            return 0.0

    def get_recent_transactions(self, limit: int = 15) -> list[tuple]:
        """Return recent income and expense rows merged, ordered newest first.

        Columns: (type_str, source_label, amount, date_str)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 'Entrée',
                   TRIM(COALESCE(S.last_name_fr, '') || ' ' || COALESCE(S.first_name_fr, '')),
                   COALESCE(P.amount_paid, 0),
                   CAST(P.transaction_date AS VARCHAR(10)) AS t_date
            FROM Payments P
            LEFT JOIN Students S ON P.student_id = S.id
            UNION ALL
            SELECT 'Sortie', COALESCE(description, '-'), COALESCE(amount, 0), CAST(expense_date AS VARCHAR(10)) AS t_date
            FROM Expenses
            ORDER BY t_date DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()

    def get_school_info(self) -> tuple | None:
        """Return a single row from SchoolInfo table."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM SchoolInfo LIMIT 1")
        return cursor.fetchone()

    def get_late_dues_students(self, year_id: int, days_overdue: int = 30, limit: int = 20) -> list[tuple]:
        """Return (full_name, total_debt) for students with unpaid dues older than days_overdue."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT S.first_name_fr || ' ' || S.last_name_fr,
                   SUM(SD.net_amount) AS total_debt
            FROM StudentDues SD
            JOIN Students S ON SD.student_id = S.id
            WHERE SD.is_paid = 0
              AND SD.year_id = %s
              AND SD.due_date < CURRENT_DATE - (%s || ' days')::INTERVAL
            GROUP BY S.id, S.first_name_fr, S.last_name_fr
            ORDER BY total_debt DESC
            LIMIT %s
            """,
            (year_id, days_overdue, limit),
        )
        return cursor.fetchall()

    def get_total_revenue(self, year_id: int) -> float:
        """Return total payments received for an academic year."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(amount_paid), 0) FROM Payments WHERE year_id = %s",
            (year_id,),
        )
        row = cursor.fetchone()
        return float(row[0]) if row else 0.0

    # ── Fees setup ─────────────────────────────────────────

    def upsert_registration_fee(self, class_id: int, amount: float) -> None:
        """Delete then re-insert the registration fee for a class."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM RegistrationFees WHERE class_id=%s", (class_id,))
        cursor.execute(
            "INSERT INTO RegistrationFees (class_id, amount) VALUES (%s, %s)",
            (class_id, amount),
        )

    def get_registration_fees_table(self) -> list:
        """Return (class_name_fr, amount) for all registration fees."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT C.class_name_fr, R.amount" " FROM RegistrationFees R" " JOIN Classes C ON R.class_id = C.id"
        )
        return cursor.fetchall()

    def save_monthly_fee_schedule(self, class_id: int, entries: list) -> None:
        """Replace all MonthlyFeeSchedule rows for a class.
        entries: list of (month_index, month_name, amount)
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM MonthlyFeeSchedule WHERE class_id=%s", (class_id,))
        for month_index, month_name, amount in entries:
            cursor.execute(
                "INSERT INTO MonthlyFeeSchedule (class_id, month_index, month_name, amount)" " VALUES (%s, %s, %s, %s)",
                (class_id, month_index, month_name, amount),
            )

    def get_fees_comparison_report(self) -> list:
        """Return (class_name, registration_fee, monthly_total) for all classes."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT C.class_name_fr,"
            "       COALESCE(RF.amount, 0) AS registration_fee,"
            "       COALESCE((SELECT SUM(MS.amount) FROM MonthlyFeeSchedule MS"
            "                 WHERE MS.class_id = C.id), 0) AS monthly_total"
            " FROM Classes C"
            " LEFT JOIN RegistrationFees RF ON RF.class_id = C.id"
            " ORDER BY C.sort_order, C.class_name_fr"
        )
        return cursor.fetchall()

    def get_fees_projection_report(self, year_id: int) -> list:
        """Return (class_name, active_students, registration_fee, monthly_total) for projection."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT C.class_name_fr,"
            "       COALESCE((SELECT COUNT(SCN.student_id) FROM StudentClassNumbers SCN"
            "                 JOIN Students S ON S.id = SCN.student_id"
            "                 WHERE SCN.class_id = C.id AND SCN.year_id = %s"
            "                   AND S.status = 'Active'), 0) AS active_students,"
            "       COALESCE(RF.amount, 0) AS registration_fee,"
            "       COALESCE((SELECT SUM(MS.amount) FROM MonthlyFeeSchedule MS"
            "                 WHERE MS.class_id = C.id), 0) AS monthly_total"
            " FROM Classes C"
            " LEFT JOIN RegistrationFees RF ON RF.class_id = C.id"
            " ORDER BY C.sort_order, C.class_name_fr",
            (year_id,),
        )
        return cursor.fetchall()

    # --- Expenses ---

    def insert_expense(self, category: str, description: str, amount: float, date_str: str, paid_to: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO Expenses (category, description, amount, expense_date, paid_to) VALUES (%s, %s, %s, %s, %s)",
            (category, description, amount, date_str, paid_to),
        )

    def list_recent_expenses(self, limit: int = 50) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, category, description, paid_to, amount, expense_date FROM Expenses ORDER BY expense_date DESC LIMIT %s",
            (limit,),
        )
        return cursor.fetchall()

    def get_expenses_by_category(self, from_date: str, to_date_full: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT category, COUNT(*), COALESCE(SUM(amount), 0)
            FROM Expenses
            WHERE CAST(expense_date AS TIMESTAMP) BETWEEN CAST(%s AS TIMESTAMP) AND CAST(%s AS TIMESTAMP)
            GROUP BY category
            ORDER BY COALESCE(SUM(amount), 0) DESC
            """,
            (from_date, to_date_full),
        )
        return cursor.fetchall()

    def get_cashflow_expenses_by_month(self, from_date: str, to_date_full: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TO_CHAR(CAST(expense_date AS TIMESTAMP), 'YYYY-MM') AS period, COALESCE(SUM(amount), 0)
            FROM Expenses
            WHERE CAST(expense_date AS TIMESTAMP) BETWEEN CAST(%s AS TIMESTAMP) AND CAST(%s AS TIMESTAMP)
            GROUP BY period
            """,
            (from_date, to_date_full),
        )
        return cursor.fetchall()

    def get_cashflow_revenues_by_month(self, from_date: str, to_date_full: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TO_CHAR(CAST(transaction_date AS TIMESTAMP), 'YYYY-MM') AS period, COALESCE(SUM(amount_paid), 0)
            FROM Payments
            WHERE CAST(transaction_date AS TIMESTAMP) BETWEEN CAST(%s AS TIMESTAMP) AND CAST(%s AS TIMESTAMP)
            GROUP BY period
            """,
            (from_date, to_date_full),
        )
        return cursor.fetchall()

    def get_expense_detail_list(self, from_date: str, to_date_full: str, limit: int = 500) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT expense_date, category, description, paid_to, amount
            FROM Expenses
            WHERE CAST(expense_date AS TIMESTAMP) BETWEEN CAST(%s AS TIMESTAMP) AND CAST(%s AS TIMESTAMP)
            ORDER BY expense_date DESC, id DESC
            LIMIT %s
            """,
            (from_date, to_date_full, limit),
        )
        return cursor.fetchall()

    # --- Payroll ---

    def list_active_staff_with_salary(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id,
                   TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')),
                   role,
                   contract_type,
                   salary_base,
                   hourly_rate
            FROM Staff
            WHERE status='Actif'
            """
        )
        return cursor.fetchall()

    def get_salary_slip_exists(self, staff_id: int, month_str: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM SalarySlips WHERE staff_id=%s AND month_str=%s",
            (staff_id, month_str),
        )
        return cursor.fetchone() is not None

    def get_staff_attendance_times(self, staff_id: int, start_date: str, end_date: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT check_in_time, check_out_time
            FROM StaffAttendance
            WHERE staff_id=%s AND attendance_date >= %s AND attendance_date < %s
            """,
            (staff_id, start_date, end_date),
        )
        return cursor.fetchall()

    def insert_salary_slip(
        self,
        staff_id: int,
        month_str: str,
        basic_amount: float,
        hours_worked: float,
        bonuses: float,
        deductions: float,
        net_amount: float,
        payment_date: str,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO SalarySlips (staff_id, month_str, basic_amount, hours_worked, bonuses, deductions, net_amount, payment_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (staff_id, month_str, basic_amount, hours_worked, bonuses, deductions, net_amount, payment_date),
        )

    def get_staff_name_role(self, staff_id: int) -> tuple | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT first_name || ' ' || last_name, role FROM Staff WHERE id=%s",
            (staff_id,),
        )
        return cursor.fetchone()
