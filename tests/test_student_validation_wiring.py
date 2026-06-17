"""F2 — student CRUD screens reject invalid data before touching the database.

validate_student existed but was not wired into the save flow. Both
_save_new_student and _save_edit_student must validate first and abort (showing
a warning) so invalid data never reaches StudentRepository / the DB.

Built via __new__ + patched module globals to avoid a real Qt window or DB.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import student_management
from student_management import ModernStudentManagement

INVALID = {"first_name_fr": "", "last_name_fr": "", "first_name_ar": ""}  # required fields blank
VALID = {
    "first_name_fr": "Awa",
    "last_name_fr": "Diop",
    "first_name_ar": "عوا",
    "gender": "F",
    "parent_email": "p@x.com",
    "parent_phone": "771234567",
}


def _win():
    return ModernStudentManagement.__new__(ModernStudentManagement)


class TestSaveNewStudentValidation:
    def test_invalid_blocks_db_write_and_warns(self):
        win = _win()
        with (
            patch.object(student_management, "QMessageBox") as msgbox,
            patch.object(student_management, "DatabaseManager") as db,
        ):
            win._save_new_student(dict(INVALID))
        msgbox.warning.assert_called_once()  # user told why
        db.assert_not_called()  # nothing persisted

    def test_valid_proceeds_to_persist(self):
        win = _win()
        with (
            patch.object(student_management, "QMessageBox") as msgbox,
            patch.object(student_management, "DatabaseManager") as db,
            patch.object(win, "_persist_photo", return_value=None),
            patch.object(win, "refresh_student_list"),
            patch.object(student_management, "ToastNotification"),
        ):
            win._save_new_student(dict(VALID))
        msgbox.warning.assert_not_called()  # passed validation
        db.assert_called()  # reached the persistence path


class TestSaveEditStudentValidation:
    def test_invalid_blocks_db_write_and_warns(self):
        win = _win()
        with (
            patch.object(student_management, "QMessageBox") as msgbox,
            patch.object(student_management, "DatabaseManager") as db,
        ):
            win._save_edit_student(42, dict(INVALID))
        msgbox.warning.assert_called_once()
        db.assert_not_called()
