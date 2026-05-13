"""
tests/test_validators_extended.py
تغطية الفروع غير المختبرة: validate_user, validate_expense,
has_errors, وحالات الحافة في validate_student / validate_staff.
"""

import pytest
from datetime import date

from validators import (
    validate_student,
    validate_staff,
    validate_payment,
    validate_grade,
    validate_password_strength,
    validate_user,
    validate_expense,
    format_errors,
    has_errors,
)


# ─────────────────────────────────────────────────────────────
# validate_student — فروع إضافية
# ─────────────────────────────────────────────────────────────
class TestValidateStudentExtra:

    def _base(self):
        return {
            "first_name_fr": "Marie",
            "last_name_fr": "Diallo",
            "first_name_ar": "ماري",
        }

    def test_birth_date_before_1940(self):
        data = {**self._base(), "birth_date": date(1930, 1, 1)}
        errors = validate_student(data)
        assert any("1940" in e for e in errors)

    def test_invalid_gender_value(self):
        data = {**self._base(), "gender": "X"}
        errors = validate_student(data)
        assert any("جنس" in e or "gender" in e.lower() for e in errors)

    def test_valid_gender_arabic_male(self):
        data = {**self._base(), "gender": "ذكر"}
        assert validate_student(data) == []

    def test_valid_gender_arabic_female(self):
        data = {**self._base(), "gender": "أنثى"}
        assert validate_student(data) == []

    def test_invalid_parent_email(self):
        data = {**self._base(), "parent_email": "notanemail"}
        errors = validate_student(data)
        assert any("بريد" in e or "email" in e.lower() for e in errors)

    def test_valid_parent_email(self):
        data = {**self._base(), "parent_email": "parent@example.com"}
        assert validate_student(data) == []

    def test_invalid_parent_phone(self):
        data = {**self._base(), "parent_phone": "abc-xyz"}
        errors = validate_student(data)
        assert any("هاتف" in e or "phone" in e.lower() for e in errors)

    def test_valid_parent_phone_with_plus(self):
        data = {**self._base(), "parent_phone": "+221 77 123 45 67"}
        assert validate_student(data) == []

    def test_missing_first_name_ar(self):
        data = {"first_name_fr": "Marie", "last_name_fr": "Diallo", "first_name_ar": ""}
        errors = validate_student(data)
        assert any("AR" in e for e in errors)


# ─────────────────────────────────────────────────────────────
# validate_staff — فروع إضافية
# ─────────────────────────────────────────────────────────────
class TestValidateStaffExtra:

    def _base(self):
        return {"first_name": "Fatou", "last_name": "Ndiaye", "role": "Professeur"}

    def test_invalid_salary(self):
        data = {**self._base(), "salary_base": "notanumber"}
        errors = validate_staff(data)
        assert any("راتب" in e for e in errors)

    def test_zero_salary_ok(self):
        data = {**self._base(), "salary_base": 0}
        assert validate_staff(data) == []

    def test_negative_salary(self):
        data = {**self._base(), "salary_base": -500}
        errors = validate_staff(data)
        assert any("سالب" in e or "سالباً" in e for e in errors)

    def test_missing_first_name(self):
        data = {"first_name": "  ", "last_name": "Ndiaye", "role": "Prof"}
        errors = validate_staff(data)
        assert any("الاسم" in e for e in errors)

    def test_invalid_phone(self):
        data = {**self._base(), "phone": "not-a-number"}
        errors = validate_staff(data)
        assert any("هاتف" in e for e in errors)


# ─────────────────────────────────────────────────────────────
# validate_payment — فروع إضافية
# ─────────────────────────────────────────────────────────────
class TestValidatePaymentExtra:

    def test_invalid_payment_type(self):
        errors = validate_payment({"amount_paid": 1000, "payment_type": "Bitcoin"})
        assert any("نوع" in e for e in errors)

    def test_valid_cheque_type(self):
        assert validate_payment({"amount_paid": 1000, "payment_type": "Chèque"}) == []

    def test_valid_mobile_money(self):
        assert validate_payment({"amount_paid": 500, "payment_type": "Mobile Money"}) == []

    def test_invalid_total_due_non_numeric_ignored(self):
        """total_due non-numeric → on ignore la vérification du dépassement"""
        errors = validate_payment({"amount_paid": 999999, "total_due": "N/A"})
        assert all("dépasse" not in e and "يتجاوز" not in e for e in errors)


# ─────────────────────────────────────────────────────────────
# validate_grade — fرع string score
# ─────────────────────────────────────────────────────────────
class TestValidateGradeExtra:

    def test_empty_string_score(self):
        errors = validate_grade({"score": "", "max_score": 20})
        assert any("مطلوب" in e for e in errors)

    def test_invalid_max_score_defaults_to_20(self):
        """max_score غير رقمي → يُستخدم 20 كافتراضي"""
        errors = validate_grade({"score": 15, "max_score": "invalid"})
        assert errors == []

    def test_score_exactly_zero(self):
        assert validate_grade({"score": 0, "max_score": 20}) == []


# ─────────────────────────────────────────────────────────────
# validate_user
# ─────────────────────────────────────────────────────────────
class TestValidateUser:

    def _valid(self):
        return {
            "username": "prof_ali",
            "email": "ali@school.sn",
            "role": "Prof",
            "password": "SecurePass1",
        }

    def test_valid_new_user(self):
        assert validate_user(self._valid(), is_new=True) == []

    def test_missing_username(self):
        data = {**self._valid(), "username": ""}
        errors = validate_user(data)
        assert any("مستخدم" in e for e in errors)

    def test_short_username(self):
        data = {**self._valid(), "username": "ab"}
        errors = validate_user(data)
        assert any("قصير" in e for e in errors)

    def test_invalid_username_chars(self):
        data = {**self._valid(), "username": "user name!"}
        errors = validate_user(data)
        assert any("أحرف" in e for e in errors)

    def test_invalid_email(self):
        data = {**self._valid(), "email": "bademail"}
        errors = validate_user(data)
        assert any("بريد" in e or "email" in e.lower() for e in errors)

    def test_invalid_role(self):
        data = {**self._valid(), "role": "SuperHero"}
        errors = validate_user(data)
        assert any("الدور" in e or "role" in e.lower() for e in errors)

    def test_valid_roles(self):
        for role in ("Admin", "Comptable", "Secretaire", "Pédagogique", "Prof"):
            data = {**self._valid(), "role": role}
            assert validate_user(data, is_new=False) == [], f"role '{role}' should be valid"

    def test_new_user_weak_password(self):
        data = {**self._valid(), "password": "abc"}
        errors = validate_user(data, is_new=True)
        assert len(errors) > 0

    def test_existing_user_no_password_check(self):
        """is_new=False → لا تحقق من كلمة المرور"""
        data = {"username": "admin", "role": "Admin"}
        errors = validate_user(data, is_new=False)
        assert all("مرور" not in e for e in errors)

    def test_empty_role_allowed(self):
        """role فارغ → لا خطأ (اختياري)"""
        data = {**self._valid(), "role": ""}
        errors = validate_user(data, is_new=False)
        assert all("الدور" not in e for e in errors)


# ─────────────────────────────────────────────────────────────
# validate_expense
# ─────────────────────────────────────────────────────────────
class TestValidateExpense:

    def _valid(self):
        return {
            "amount": 5000,
            "category": "Fournitures",
            "description": "Achat cahiers",
        }

    def test_valid_expense(self):
        assert validate_expense(self._valid()) == []

    def test_missing_amount(self):
        data = {**self._valid(), "amount": None}
        errors = validate_expense(data)
        assert any("مبلغ" in e for e in errors)

    def test_zero_amount(self):
        data = {**self._valid(), "amount": 0}
        errors = validate_expense(data)
        assert any("صفر" in e or "0" in e or "أكبر" in e for e in errors)

    def test_negative_amount(self):
        data = {**self._valid(), "amount": -100}
        errors = validate_expense(data)
        assert any("صفر" in e or "أكبر" in e for e in errors)

    def test_non_numeric_amount(self):
        data = {**self._valid(), "amount": "abc"}
        errors = validate_expense(data)
        assert any("رقم" in e for e in errors)

    def test_missing_category(self):
        data = {**self._valid(), "category": ""}
        errors = validate_expense(data)
        assert any("فئة" in e for e in errors)

    def test_missing_description(self):
        data = {**self._valid(), "description": ""}
        errors = validate_expense(data)
        assert any("وصف" in e for e in errors)


# ─────────────────────────────────────────────────────────────
# has_errors + format_errors
# ─────────────────────────────────────────────────────────────
class TestHelpers:

    def test_has_errors_true_when_any_nonempty(self):
        assert has_errors([], ["خطأ ما"], []) is True

    def test_has_errors_false_when_all_empty(self):
        assert has_errors([], [], []) is False

    def test_has_errors_single_nonempty(self):
        assert has_errors(["err"]) is True

    def test_has_errors_single_empty(self):
        assert has_errors([]) is False

    def test_format_errors_non_empty(self):
        result = format_errors(["خطأ 1", "خطأ 2"])
        assert "خطأ 1" in result
        assert "خطأ 2" in result
        assert result.startswith("•")

    def test_format_errors_empty(self):
        assert format_errors([]) == ""
