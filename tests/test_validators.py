"""Tests for validators.py"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from validators import (
    validate_student,
    validate_staff,
    validate_payment,
    validate_grade,
    validate_password_strength,
    format_errors,
)


# ──────────────────────────────────────────────
# validate_student
# ──────────────────────────────────────────────

class TestValidateStudent:
    def _base(self):
        return {
            "first_name_fr": "Jean",
            "last_name_fr": "Dupont",
            "first_name_ar": "جان",
            "birth_date": date(2010, 5, 1),
            "gender": "M",
            "parent_email": "parent@school.sn",
            "parent_phone": "771234567",
        }

    def test_valid_data_no_errors(self):
        assert validate_student(self._base()) == []

    def test_missing_first_name_fr(self):
        d = self._base(); d["first_name_fr"] = ""
        errors = validate_student(d)
        assert any("FR" in e or "Prénom" in e for e in errors)

    def test_missing_last_name_fr(self):
        d = self._base(); d["last_name_fr"] = "  "
        errors = validate_student(d)
        assert any("Nom" in e for e in errors)

    def test_future_birth_date(self):
        d = self._base(); d["birth_date"] = date.today() + timedelta(days=1)
        errors = validate_student(d)
        assert any("مستقبل" in e or "avenir" in e.lower() or "futur" in e.lower() for e in errors)

    def test_very_old_birth_date(self):
        d = self._base(); d["birth_date"] = date(1930, 1, 1)
        errors = validate_student(d)
        assert any("1940" in e for e in errors)

    def test_invalid_gender(self):
        d = self._base(); d["gender"] = "X"
        errors = validate_student(d)
        assert any("جنس" in e or "gender" in e.lower() for e in errors)

    def test_invalid_email(self):
        d = self._base(); d["parent_email"] = "notanemail"
        errors = validate_student(d)
        assert any("@" in e or "email" in e.lower() or "بريد" in e for e in errors)

    def test_invalid_phone(self):
        d = self._base(); d["parent_phone"] = "abc-def"
        errors = validate_student(d)
        assert any("هاتف" in e or "phone" in e.lower() for e in errors)

    def test_none_birth_date_no_error(self):
        d = self._base(); d["birth_date"] = None
        assert validate_student(d) == []


# ──────────────────────────────────────────────
# validate_staff
# ──────────────────────────────────────────────

class TestValidateStaff:
    def _base(self):
        return {
            "first_name": "Ahmed",
            "last_name": "Diallo",
            "role": "Enseignant",
            "phone": "776543210",
            "email": "ahmed@school.sn",
            "salary_base": 150000,
        }

    def test_valid_data_no_errors(self):
        assert validate_staff(self._base()) == []

    def test_missing_first_name(self):
        d = self._base(); d["first_name"] = ""
        assert validate_staff(d) != []

    def test_missing_role(self):
        d = self._base(); d["role"] = ""
        assert validate_staff(d) != []

    def test_negative_salary(self):
        d = self._base(); d["salary_base"] = -500
        errors = validate_staff(d)
        assert any("راتب" in e or "salaire" in e.lower() for e in errors)

    def test_invalid_email(self):
        d = self._base(); d["email"] = "bademail"
        assert validate_staff(d) != []


# ──────────────────────────────────────────────
# validate_payment
# ──────────────────────────────────────────────

class TestValidatePayment:
    def test_valid_payment(self):
        assert validate_payment({"amount_paid": 5000}) == []

    def test_missing_amount(self):
        errors = validate_payment({})
        assert errors

    def test_zero_amount(self):
        errors = validate_payment({"amount_paid": 0})
        assert errors

    def test_negative_amount(self):
        errors = validate_payment({"amount_paid": -100})
        assert errors

    def test_amount_exceeds_due(self):
        errors = validate_payment({"amount_paid": 20000, "total_due": 10000})
        assert errors

    def test_amount_within_due(self):
        assert validate_payment({"amount_paid": 9999, "total_due": 10000}) == []

    def test_amount_equals_due(self):
        assert validate_payment({"amount_paid": 10000, "total_due": 10000}) == []

    def test_non_numeric_amount(self):
        errors = validate_payment({"amount_paid": "abc"})
        assert errors

    def test_valid_payment_type(self):
        assert validate_payment({"amount_paid": 1000, "payment_type": "Espèces"}) == []

    def test_invalid_payment_type(self):
        errors = validate_payment({"amount_paid": 1000, "payment_type": "Bitcoin"})
        assert errors


# ──────────────────────────────────────────────
# validate_grade
# ──────────────────────────────────────────────

class TestValidateGrade:
    def test_valid_grade(self):
        assert validate_grade({"score": 15.0}) == []

    def test_missing_score(self):
        assert validate_grade({}) != []

    def test_negative_score(self):
        assert validate_grade({"score": -1}) != []

    def test_score_exceeds_max(self):
        errors = validate_grade({"score": 25.0, "max_score": 20.0})
        assert errors

    def test_score_equals_max(self):
        assert validate_grade({"score": 20.0, "max_score": 20.0}) == []

    def test_non_numeric_score(self):
        assert validate_grade({"score": "abc"}) != []


# ──────────────────────────────────────────────
# validate_password_strength
# ──────────────────────────────────────────────

class TestValidatePasswordStrength:
    def test_strong_password(self):
        assert validate_password_strength("Str0ng!Pass") == []

    def test_too_short(self):
        errors = validate_password_strength("Ab1!", min_length=8)
        assert errors

    def test_no_uppercase_still_passes(self):
        # validate_password_strength only requires letter + digit, not uppercase
        assert validate_password_strength("weakpass1!") == []

    def test_no_digit(self):
        errors = validate_password_strength("WeakPass!!")
        assert errors

    def test_empty_password(self):
        assert validate_password_strength("") != []


# ──────────────────────────────────────────────
# format_errors
# ──────────────────────────────────────────────

class TestFormatErrors:
    def test_formats_list(self):
        result = format_errors(["Error 1", "Error 2"])
        assert "Error 1" in result
        assert "Error 2" in result

    def test_empty_list(self):
        assert format_errors([]) == ""
