"""Phase 4 — FinanceRepository tests.

Covers finance_repo.py (31% → ~100%).
"""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from src.data.finance_repo import FinanceRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    repo = FinanceRepository(conn)
    return repo, cursor


# ===========================================================================
# Payment recording
# ===========================================================================


class TestFinanceRecordPayment:
    def test_no_allocations(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (42,)
        result = repo.record_payment(
            student_id=1,
            year_id=1,
            transaction_date="2026-01-10",
            total_due=1000.0,
            amount_received=500.0,
            description="Partial payment",
            allocations=[],
        )
        assert result == 42

    def test_single_allocation_triggers_paid(self):
        repo, cursor = _make_repo()
        # payment_id=5, then due_status: net=100, total_paid=100 → marks paid
        cursor.fetchone.side_effect = [(5,), (100.0, 100.0)]
        result = repo.record_payment(
            student_id=1,
            year_id=1,
            transaction_date="2026-01-10",
            total_due=100.0,
            amount_received=100.0,
            description="Full payment",
            allocations=[{"id": 10, "amount_due": 100.0}],
        )
        assert result == 5
        # UPDATE StudentDues SET is_paid=1 should have been called
        execute_calls = [str(c[0][0]).strip()[:20] for c in cursor.execute.call_args_list]
        assert any("UPDATE StudentDues" in c for c in [str(c) for c in cursor.execute.call_args_list])

    def test_single_allocation_partial_no_paid_update(self):
        repo, cursor = _make_repo()
        # due: net=100, paid so far=50 → not fully paid
        cursor.fetchone.side_effect = [(3,), (100.0, 50.0)]
        result = repo.record_payment(
            student_id=1,
            year_id=1,
            transaction_date="2026-01-10",
            total_due=100.0,
            amount_received=50.0,
            description="Partial",
            allocations=[{"id": 7, "amount_due": 100.0}],
        )
        assert result == 3

    def test_amount_runs_out_early(self):
        repo, cursor = _make_repo()
        # Only the first allocation gets paid (amount_received < total of 2 dues)
        cursor.fetchone.side_effect = [(1,), (100.0, 50.0)]
        result = repo.record_payment(
            student_id=1,
            year_id=1,
            transaction_date="2026-01-10",
            total_due=200.0,
            amount_received=50.0,
            description="Limited",
            allocations=[
                {"id": 1, "amount_due": 50.0},
                {"id": 2, "amount_due": 50.0},
            ],
        )
        assert result == 1


# ===========================================================================
# Payment history & receipt
# ===========================================================================


class TestFinanceListPaymentHistory:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "2026-01-10", "desc", 1000.0, 1000.0)]
        result = repo.list_payment_history(student_id=1)
        assert result == [(1, "2026-01-10", "desc", 1000.0, 1000.0)]


class TestFinanceGetPaymentReceiptData:
    def test_found(self):
        repo, cursor = _make_repo()
        row = (1, "2026-01-10", "Ali Ben", "CE1", 1000.0, 0.0, 1000.0, 0.0, "desc")
        cursor.fetchone.return_value = row
        assert repo.get_payment_receipt_data(1) == row

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_payment_receipt_data(99) is None


# ===========================================================================
# Academic year
# ===========================================================================


class TestFinanceGetActiveYearId:
    def test_active_year_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (3,)
        assert repo.get_active_year_id() == 3

    def test_fallback_to_last(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, (2,)]
        assert repo.get_active_year_id() == 2

    def test_no_years(self):
        repo, cursor = _make_repo()
        cursor.fetchone.side_effect = [None, None]
        assert repo.get_active_year_id() == -1


# ===========================================================================
# Dues management
# ===========================================================================


class TestFinanceGetDuesForManagement:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Scolarité", "desc", 500.0, 0.0, 500.0, "2026-01-01", 0)]
        result = repo.get_dues_for_management(student_id=1, year_id=1)
        assert len(result) == 1


class TestFinanceAddDue:
    def test_executes_insert(self):
        repo, cursor = _make_repo()
        repo.add_due(
            student_id=1,
            year_id=1,
            fee_type="Scolarité",
            fee_description="Jan",
            original_amount=500.0,
            net_amount=500.0,
            due_date="2026-01-01",
        )
        cursor.execute.assert_called_once()


class TestFinanceGetDueIsPaid:
    def test_paid(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (1,)
        assert repo.get_due_is_paid(1) is True

    def test_unpaid(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (0,)
        assert repo.get_due_is_paid(1) is False

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_due_is_paid(99) is False


class TestFinanceUpdateDueDiscount:
    def test_executes_update(self):
        repo, cursor = _make_repo()
        repo.update_due_discount(due_id=1, discount_amount=50.0, net_amount=450.0)
        cursor.execute.assert_called_once()


class TestFinanceDeleteDue:
    def test_executes_delete(self):
        repo, cursor = _make_repo()
        repo.delete_due(due_id=5)
        cursor.execute.assert_called_once()


class TestFinanceCountDuesByType:
    def test_returns_count(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (3,)
        assert repo.count_dues_by_type(student_id=1, year_id=1, fee_type="Scolarité") == 3

    def test_not_found_returns_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.count_dues_by_type(student_id=1, year_id=1, fee_type="X") == 0


# ===========================================================================
# Dues export & meta
# ===========================================================================


class TestFinanceGetDuesForExport:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("Scolarité", "Jan", "2026-01-01", 500.0, 0.0, 500.0, 0)]
        result = repo.get_dues_for_export(student_id=1, year_id=1)
        assert len(result) == 1


class TestFinanceGetStudentMetaForDues:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("Ali Ben", "CE1", "2025-2026")
        result = repo.get_student_meta_for_dues(student_id=1, year_id=1)
        assert result == ("Ali Ben", "CE1", "2025-2026")

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_student_meta_for_dues(student_id=99, year_id=1) is None


# ===========================================================================
# Fee schedule
# ===========================================================================


class TestFinanceGetRegistrationFee:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (15000.0,)
        assert repo.get_registration_fee(class_id=1) == 15000.0

    def test_not_found_returns_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_registration_fee(class_id=99) == 0.0


class TestFinanceGetMonthlyFeeSchedule:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Octobre", 5000.0), (2, "Novembre", 5000.0)]
        result = repo.get_monthly_fee_schedule(class_id=1)
        assert len(result) == 2


class TestFinanceListStudentsInClass:
    def test_returns_ids(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1,), (2,), (3,)]
        result = repo.list_students_in_class(class_id=1, year_id=1)
        assert result == [(1,), (2,), (3,)]


# ===========================================================================
# Dashboard aggregates
# ===========================================================================


class TestFinanceGetTotalIncome:
    def test_returns_float(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (50000.0,)
        assert repo.get_total_income() == 50000.0

    def test_returns_zero_when_null(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None,)
        assert repo.get_total_income() == 0.0

    def test_exception_returns_zero(self):
        repo, cursor = _make_repo()
        # float("not_a_number") raises ValueError → except block returns 0.0
        cursor.fetchone.return_value = ("not_a_number",)
        result = repo.get_total_income()
        assert result == 0.0


class TestFinanceGetTotalExpenses:
    def test_returns_float(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (12000.0,)
        assert repo.get_total_expenses() == 12000.0

    def test_returns_zero_when_null(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None,)
        assert repo.get_total_expenses() == 0.0

    def test_exception_returns_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("not_a_number",)
        assert repo.get_total_expenses() == 0.0


class TestFinanceGetTotalInventoryValue:
    def test_returns_float(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (7500.0,)
        assert repo.get_total_inventory_value() == 7500.0

    def test_returns_zero_when_null(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (None,)
        assert repo.get_total_inventory_value() == 0.0

    def test_exception_returns_zero(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("not_a_number",)
        assert repo.get_total_inventory_value() == 0.0


class TestFinanceGetRecentTransactions:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [
            ("Entrée", "Ali Ben", 5000.0, "2026-01-10"),
            ("Sortie", "Fournitures", 200.0, "2026-01-09"),
        ]
        result = repo.get_recent_transactions(limit=10)
        assert len(result) == 2

    def test_default_limit(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        repo.get_recent_transactions()
        call_args = cursor.execute.call_args
        assert 15 in call_args[0][1]


class TestFinanceGetSchoolInfo:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (1, "École El Malick")
        assert repo.get_school_info() == (1, "École El Malick")

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_school_info() is None


# ===========================================================================
# Late dues & revenue
# ===========================================================================


class TestFinanceGetLateDuesStudents:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("Ali Ben", 25000.0)]
        result = repo.get_late_dues_students(year_id=1, days_overdue=30, limit=20)
        assert result == [("Ali Ben", 25000.0)]

    def test_default_params(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        repo.get_late_dues_students(year_id=1)
        cursor.execute.assert_called_once()


class TestFinanceGetTotalRevenue:
    def test_returns_float(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (100000.0,)
        assert repo.get_total_revenue(year_id=1) == 100000.0

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_total_revenue(year_id=1) == 0.0


# ===========================================================================
# Fees setup
# ===========================================================================


class TestFinanceUpsertRegistrationFee:
    def test_deletes_then_inserts(self):
        repo, cursor = _make_repo()
        repo.upsert_registration_fee(class_id=1, amount=15000.0)
        assert cursor.execute.call_count == 2


class TestFinanceGetRegistrationFeesTable:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("CE1", 15000.0), ("CE2", 15000.0)]
        result = repo.get_registration_fees_table()
        assert len(result) == 2


class TestFinanceSaveMonthlyFeeSchedule:
    def test_deletes_and_inserts_entries(self):
        repo, cursor = _make_repo()
        entries = [(1, "Octobre", 5000.0), (2, "Novembre", 5000.0)]
        repo.save_monthly_fee_schedule(class_id=1, entries=entries)
        # 1 DELETE + 2 INSERTs = 3 calls
        assert cursor.execute.call_count == 3

    def test_empty_entries(self):
        repo, cursor = _make_repo()
        repo.save_monthly_fee_schedule(class_id=1, entries=[])
        assert cursor.execute.call_count == 1  # only DELETE


class TestFinanceGetFeesComparisonReport:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("CE1", 15000.0, 45000.0)]
        result = repo.get_fees_comparison_report()
        assert len(result) == 1


class TestFinanceGetFeesProjectionReport:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("CE1", 25, 15000.0, 45000.0)]
        result = repo.get_fees_projection_report(year_id=1)
        assert len(result) == 1


# ===========================================================================
# Expenses
# ===========================================================================


class TestFinanceInsertExpense:
    def test_executes_insert(self):
        repo, cursor = _make_repo()
        repo.insert_expense(
            category="Fournitures",
            description="Papier",
            amount=500.0,
            date_str="2026-01-10",
            paid_to="Fournisseur A",
        )
        cursor.execute.assert_called_once()


class TestFinanceListRecentExpenses:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Fournitures", "Papier", "F.A", 500.0, "2026-01-10")]
        result = repo.list_recent_expenses(limit=10)
        assert len(result) == 1

    def test_default_limit(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        repo.list_recent_expenses()
        call_args = cursor.execute.call_args
        assert 50 in call_args[0][1]


class TestFinanceGetExpensesByCategory:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("Fournitures", 5, 2500.0)]
        result = repo.get_expenses_by_category("2026-01-01", "2026-01-31 23:59:59")
        assert len(result) == 1


class TestFinanceGetCashflowExpensesByMonth:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-01", 1200.0)]
        result = repo.get_cashflow_expenses_by_month("2026-01-01", "2026-01-31 23:59:59")
        assert len(result) == 1


class TestFinanceGetCashflowRevenuesByMonth:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-01", 45000.0)]
        result = repo.get_cashflow_revenues_by_month("2026-01-01", "2026-01-31 23:59:59")
        assert len(result) == 1


class TestFinanceGetExpenseDetailList:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("2026-01-10", "Fournitures", "Papier", "FA", 500.0)]
        result = repo.get_expense_detail_list("2026-01-01", "2026-01-31 23:59:59", limit=100)
        assert len(result) == 1

    def test_default_limit(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = []
        repo.get_expense_detail_list("2026-01-01", "2026-01-31 23:59:59")
        call_args = cursor.execute.call_args
        assert 500 in call_args[0][1]


# ===========================================================================
# Payroll
# ===========================================================================


class TestFinanceListActiveStaffWithSalary:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [(1, "Ahmed Diop", "Enseignant", "CDI", 150000.0, None)]
        result = repo.list_active_staff_with_salary()
        assert len(result) == 1


class TestFinanceGetSalarySlipExists:
    def test_exists(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = (1,)
        assert repo.get_salary_slip_exists(staff_id=1, month_str="2026-01") is True

    def test_not_exists(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_salary_slip_exists(staff_id=1, month_str="2026-01") is False


class TestFinanceGetStaffAttendanceTimes:
    def test_returns_list(self):
        repo, cursor = _make_repo()
        cursor.fetchall.return_value = [("08:00", "17:00"), ("08:15", "17:00")]
        result = repo.get_staff_attendance_times(staff_id=1, start_date="2026-01-01", end_date="2026-01-31")
        assert len(result) == 2


class TestFinanceInsertSalarySlip:
    def test_executes_insert(self):
        repo, cursor = _make_repo()
        repo.insert_salary_slip(
            staff_id=1,
            month_str="2026-01",
            basic_amount=150000.0,
            hours_worked=168.0,
            bonuses=10000.0,
            deductions=5000.0,
            net_amount=155000.0,
            payment_date="2026-01-31",
        )
        cursor.execute.assert_called_once()


class TestFinanceGetStaffNameRole:
    def test_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = ("Ahmed Diop", "Enseignant")
        assert repo.get_staff_name_role(1) == ("Ahmed Diop", "Enseignant")

    def test_not_found(self):
        repo, cursor = _make_repo()
        cursor.fetchone.return_value = None
        assert repo.get_staff_name_role(99) is None
