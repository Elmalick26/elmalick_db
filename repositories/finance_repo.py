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
