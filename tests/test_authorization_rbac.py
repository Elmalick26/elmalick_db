"""D3 — RBAC permission matrix coverage for services/authorization.py.

Covers the public API (can / is_allowed / get_allowed_resources / canonical_role)
plus structural and security invariants of RBAC_MATRIX. The invariant tests are
the important ones: they lock the security policy so a future edit cannot silently
grant write access to a read-only role or break a cell's shape.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from services.authorization import RBAC_MATRIX, can, canonical_role, get_allowed_resources, is_allowed

ACTIONS = ("view", "create", "update", "delete", "export", "approve", "reset")
WRITE_ACTIONS = ("create", "update", "delete", "approve", "reset")
CANONICAL_ROLES = ("Admin", "Comptable", "Secretaire", "Pédagogique", "Prof", "parent")


# ──────────────────────────────────────────────
# canonical_role
# ──────────────────────────────────────────────


class TestCanonicalRole:
    def test_teacher_alias_maps_to_prof(self):
        assert canonical_role("Teacher") == "Prof"

    def test_staff_alias_maps_to_secretaire(self):
        assert canonical_role("Staff") == "Secretaire"

    def test_canonical_role_unchanged(self):
        assert canonical_role("Admin") == "Admin"

    def test_unknown_role_returned_as_is(self):
        assert canonical_role("Ghost") == "Ghost"


# ──────────────────────────────────────────────
# can()
# ──────────────────────────────────────────────


class TestCan:
    def test_admin_has_unconditional_access(self):
        assert can("Admin", "delete", "Students") is True
        assert can("Admin", "create", "Users") is True

    def test_unknown_role_denied(self):
        assert can("Ghost", "view", "Students") is False

    def test_unknown_resource_denied(self):
        assert can("Admin", "view", "Nonexistent") is False

    def test_unknown_action_denied(self):
        assert can("Admin", "fly", "Students") is False

    def test_conditional_returned_literally(self):
        # Prof works only on own class; parent only on own child.
        assert can("Prof", "update", "Grades") == "conditional"
        assert can("Prof", "view", "Students") == "conditional"
        assert can("parent", "view", "Bulletins") == "conditional"
        assert can("parent", "export", "Bulletins") == "conditional"

    def test_alias_resolved_through_can(self):
        assert can("Teacher", "view", "Students") == "conditional"  # Teacher → Prof
        assert can("Staff", "create", "Students") is True  # Staff → Secretaire

    def test_representative_denials(self):
        assert can("Comptable", "view", "Grades") is False  # finance role, no grades
        assert can("Prof", "delete", "Students") is False
        assert can("Secretaire", "view", "Payments") is False
        assert can("parent", "view", "Users") is False

    def test_representative_allows(self):
        assert can("Comptable", "create", "Payments") is True
        assert can("Secretaire", "create", "Students") is True
        assert can("Pédagogique", "approve", "Grades") is True


# ──────────────────────────────────────────────
# is_allowed()
# ──────────────────────────────────────────────


class TestIsAllowed:
    def test_true_stays_true(self):
        assert is_allowed("Admin", "delete", "Students") is True

    def test_false_stays_false(self):
        assert is_allowed("Comptable", "view", "Grades") is False

    def test_conditional_treated_as_allowed(self):
        assert is_allowed("Prof", "update", "Grades") is True
        assert is_allowed("parent", "view", "Bulletins") is True

    def test_unknown_role_not_allowed(self):
        assert is_allowed("Ghost", "view", "Students") is False


# ──────────────────────────────────────────────
# get_allowed_resources()
# ──────────────────────────────────────────────


class TestGetAllowedResources:
    def test_includes_conditional_resources(self):
        # Prof can create grades/attendance/discipline (conditionally) — all count.
        res = get_allowed_resources("Prof", "create")
        assert set(res) == {"Grades", "Attendance", "Discipline"}

    def test_admin_view_covers_all_resources(self):
        res = get_allowed_resources("Admin", "view")
        assert set(res) == set(RBAC_MATRIX["Admin"].keys())

    def test_parent_has_no_create_resources(self):
        assert get_allowed_resources("parent", "create") == []

    def test_unknown_role_returns_empty(self):
        assert get_allowed_resources("Ghost", "view") == []

    def test_alias_resolved(self):
        assert get_allowed_resources("Teacher", "create") == get_allowed_resources("Prof", "create")


# ──────────────────────────────────────────────
# Matrix invariants — the security policy lock
# ──────────────────────────────────────────────


class TestMatrixInvariants:
    def test_all_canonical_roles_present(self):
        assert set(RBAC_MATRIX.keys()) == set(CANONICAL_ROLES)

    def test_every_cell_has_all_actions(self):
        for role, resources in RBAC_MATRIX.items():
            for resource, perms in resources.items():
                assert set(perms.keys()) == set(ACTIONS), f"{role}/{resource} missing actions"

    def test_every_value_is_valid(self):
        for role, resources in RBAC_MATRIX.items():
            for resource, perms in resources.items():
                for action, value in perms.items():
                    assert value in (True, False, "conditional"), f"{role}/{resource}/{action}={value!r}"

    def test_only_prof_and_parent_use_conditional(self):
        for role, resources in RBAC_MATRIX.items():
            for resource, perms in resources.items():
                for action, value in perms.items():
                    if value == "conditional":
                        assert role in ("Prof", "parent"), f"unexpected conditional in {role}"

    def test_parent_has_no_write_access(self):
        # Parents are read-only (own child): never create/update/delete/approve/reset.
        for resource, perms in RBAC_MATRIX["parent"].items():
            for action in WRITE_ACTIONS:
                assert perms[action] is False, f"parent must not {action} {resource}"

    def test_comptable_isolated_from_grades_and_discipline(self):
        # Finance role must have zero access to academic records.
        for resource in ("Grades", "Attendance", "Discipline"):
            for action in ACTIONS:
                assert RBAC_MATRIX["Comptable"][resource][action] is False

    def test_only_admin_can_reset_users(self):
        for role in CANONICAL_ROLES:
            expected = role == "Admin"
            assert (RBAC_MATRIX[role]["Users"]["reset"] is True) == expected
