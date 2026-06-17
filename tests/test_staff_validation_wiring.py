"""F2 — staff CRUD screen rejects invalid data before touching the database.

_save_staff_from_dialog must run validate_staff first and abort with a warning,
so invalid staff data never reaches StaffRepository / the DB.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import staff_management
from staff_management import ModernStaffManagement

INVALID = {"first_name": "", "last_name": "", "role": ""}  # required fields blank
VALID = {"first_name": "Moussa", "last_name": "Ba", "role": "Prof", "phone": "771234567", "email": "m@x.com"}


def _win():
    return ModernStaffManagement.__new__(ModernStaffManagement)


def test_invalid_staff_blocks_db_write_and_warns():
    win = _win()
    dialog = MagicMock()
    with (
        patch.object(staff_management, "QMessageBox") as msgbox,
        patch.object(staff_management, "DatabaseManager") as db,
    ):
        win._save_staff_from_dialog(dialog, dict(INVALID), None)
    msgbox.warning.assert_called_once()
    db.assert_not_called()


def test_valid_staff_proceeds_to_persist():
    win = _win()
    dialog = MagicMock()
    dialog.get_new_photo_path.return_value = None
    with (
        patch.object(staff_management, "QMessageBox"),
        patch.object(staff_management, "DatabaseManager") as db,
        patch.object(staff_management, "log_audit", MagicMock()),
    ):
        win._save_staff_from_dialog(dialog, dict(VALID), None)
    db.assert_called()  # reached persistence path (validation passed)
