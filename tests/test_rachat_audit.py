"""Manual promotion override (rachat) must be audited.

The director can override the auto-computed promotion decision in the year-end
migration preview. School policy requires this override to be authorised (RBAC,
admin-only) AND documented. This locks the documentation half: every changed
decision is written to AuditLogs with actor + student + auto -> manual.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import year_end_migration
from year_end_migration import MigrationWindow


def _win(migration_data, current_user="directeur"):
    w = MigrationWindow.__new__(MigrationWindow)
    w.migration_data = migration_data
    w.current_user = current_user
    return w


def test_override_is_audited():
    # Auto said Redouble (avg 9.5); director rescues to Admis → must be logged.
    w = _win([{"id": 7, "decision": "Redouble"}, {"id": 8, "decision": "Admis"}])
    rows = [{"student_id": 7, "decision": "Admis"}, {"student_id": 8, "decision": "Admis"}]
    conn = MagicMock()
    with patch.object(year_end_migration, "log_audit") as audit:
        n = w._audit_decision_overrides(conn, rows)
    assert n == 1
    audit.assert_called_once()
    args = audit.call_args[0]
    assert args[0] is conn
    assert args[1] == "directeur"  # actor recorded
    assert args[2] == "GRADE_DECISION_OVERRIDE"
    assert "student=7" in args[3] and "Redouble -> Admis" in args[3]


def test_no_override_no_audit():
    w = _win([{"id": 7, "decision": "Admis"}, {"id": 8, "decision": "Redouble"}])
    rows = [{"student_id": 7, "decision": "Admis"}, {"student_id": 8, "decision": "Redouble"}]
    conn = MagicMock()
    with patch.object(year_end_migration, "log_audit") as audit:
        n = w._audit_decision_overrides(conn, rows)
    assert n == 0
    audit.assert_not_called()


def test_multiple_overrides_each_logged():
    w = _win([{"id": 1, "decision": "Redouble"}, {"id": 2, "decision": "Admis"}, {"id": 3, "decision": "Admis"}])
    rows = [
        {"student_id": 1, "decision": "Admis"},  # override
        {"student_id": 2, "decision": "Exclu"},  # override
        {"student_id": 3, "decision": "Admis"},  # unchanged
    ]
    conn = MagicMock()
    with patch.object(year_end_migration, "log_audit") as audit:
        n = w._audit_decision_overrides(conn, rows)
    assert n == 2
    assert audit.call_count == 2
