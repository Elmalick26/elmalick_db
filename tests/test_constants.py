"""Tests for constants.py — sanity checks on values and role groupings."""

import pytest

import constants


class TestRoleConstants:

    def test_all_role_strings_non_empty(self):
        for role in (
            constants.ROLE_ADMIN,
            constants.ROLE_COMPTABLE,
            constants.ROLE_SECRETAIRE,
            constants.ROLE_PEDAGOGIQUE,
            constants.ROLE_PROF,
            constants.ROLE_PARENT,
        ):
            assert isinstance(role, str) and role, f"Role should be non-empty string: {role!r}"

    def test_all_roles_tuple_contains_staff_roles(self):
        for r in (
            constants.ROLE_ADMIN,
            constants.ROLE_COMPTABLE,
            constants.ROLE_SECRETAIRE,
            constants.ROLE_PEDAGOGIQUE,
            constants.ROLE_PROF,
        ):
            assert r in constants.ALL_ROLES

    def test_parent_not_in_staff_roles(self):
        assert constants.ROLE_PARENT not in constants.ALL_ROLES

    def test_financial_roles_subset_of_all_roles(self):
        for r in constants.FINANCIAL_ROLES:
            assert r in constants.ALL_ROLES

    def test_academic_roles_subset_of_all_roles(self):
        for r in constants.ACADEMIC_ROLES:
            assert r in constants.ALL_ROLES

    def test_no_duplicate_roles_in_all_roles(self):
        assert len(constants.ALL_ROLES) == len(set(constants.ALL_ROLES))


class TestPaginationConstants:

    def test_page_size_default_positive(self):
        assert constants.PAGE_SIZE_DEFAULT > 0

    def test_page_size_large_greater_than_default(self):
        assert constants.PAGE_SIZE_LARGE > constants.PAGE_SIZE_DEFAULT

    def test_page_size_small_less_than_default(self):
        assert constants.PAGE_SIZE_SMALL < constants.PAGE_SIZE_DEFAULT

    def test_page_size_default_value(self):
        assert constants.PAGE_SIZE_DEFAULT == 50


class TestFinanceConstants:

    def test_currency_symbol_non_empty(self):
        assert isinstance(constants.CURRENCY_SYMBOL, str) and constants.CURRENCY_SYMBOL

    def test_late_fee_rate_between_0_and_1(self):
        assert 0 < constants.LATE_FEE_RATE < 1

    def test_payment_receipt_prefix_non_empty(self):
        assert constants.PAYMENT_RECEIPT_PREFIX


class TestAcademicConstants:

    def test_grade_min_zero(self):
        assert constants.GRADE_MIN == 0.0

    def test_grade_max_positive(self):
        assert constants.GRADE_MAX > 0

    def test_pass_average_between_min_and_max(self):
        assert constants.GRADE_MIN < constants.PASS_AVERAGE < constants.GRADE_MAX

    def test_pass_average_value(self):
        assert constants.PASS_AVERAGE == 10.0

    def test_grade_precision_non_negative(self):
        assert constants.GRADE_PRECISION >= 0

    def test_student_code_prefix_non_empty(self):
        assert constants.STUDENT_CODE_PREFIX


class TestUIConstants:

    def test_toast_duration_positive(self):
        assert constants.TOAST_DURATION_MS > 0

    def test_session_timeout_positive(self):
        assert constants.SESSION_TIMEOUT_MINUTES > 0

    def test_db_retry_max_at_least_one(self):
        assert constants.DB_RETRY_MAX >= 1

    def test_db_retry_delay_positive(self):
        assert constants.DB_RETRY_DELAY_S > 0


class TestAttendanceConstants:

    def test_absence_critical_percent_valid_range(self):
        assert 0 < constants.ABSENCE_CRITICAL_PERCENT < 100

    def test_late_arrival_minutes_positive(self):
        assert constants.LATE_ARRIVAL_MINUTES > 0
