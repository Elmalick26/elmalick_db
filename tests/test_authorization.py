"""Unit tests for services/authorization.py — T5.3 RBAC PermissionChecker."""

import pytest

from services.authorization import can, canonical_role, get_allowed_resources, is_allowed


# ─────────────────────────────────────────────────────────────────────────────
# canonical_role()
# ─────────────────────────────────────────────────────────────────────────────
class TestCanonicalRole:
    def test_teacher_maps_to_prof(self):
        assert canonical_role("Teacher") == "Prof"

    def test_staff_maps_to_secretaire(self):
        assert canonical_role("Staff") == "Secretaire"

    def test_admin_unchanged(self):
        assert canonical_role("Admin") == "Admin"

    def test_unknown_role_unchanged(self):
        assert canonical_role("Ghost") == "Ghost"


# ─────────────────────────────────────────────────────────────────────────────
# can() — Admin
# ─────────────────────────────────────────────────────────────────────────────
class TestAdminPermissions:
    def test_admin_can_delete_students(self):
        assert can("Admin", "delete", "Students") is True

    def test_admin_can_view_audit_logs(self):
        assert can("Admin", "view", "AuditLogs") is True

    def test_admin_cannot_delete_audit_logs(self):
        assert can("Admin", "delete", "AuditLogs") is False

    def test_admin_can_reset_users(self):
        assert can("Admin", "reset", "Users") is True


# ─────────────────────────────────────────────────────────────────────────────
# can() — Comptable
# ─────────────────────────────────────────────────────────────────────────────
class TestComptablePermissions:
    def test_comptable_can_view_payments(self):
        assert can("Comptable", "view", "Payments") is True

    def test_comptable_cannot_delete_payments(self):
        assert can("Comptable", "delete", "Payments") is False

    def test_comptable_cannot_view_grades(self):
        assert can("Comptable", "view", "Grades") is False

    def test_comptable_cannot_access_users(self):
        assert can("Comptable", "view", "Users") is False

    def test_comptable_can_view_dues(self):
        assert can("Comptable", "view", "Dues") is True


# ─────────────────────────────────────────────────────────────────────────────
# can() — Prof / Teacher alias
# ─────────────────────────────────────────────────────────────────────────────
class TestProfPermissions:
    def test_prof_can_update_grades_with_condition(self):
        assert can("Prof", "update", "Grades") == "conditional"

    def test_prof_cannot_delete_students(self):
        assert can("Prof", "delete", "Students") is False

    def test_prof_cannot_view_payments(self):
        assert can("Prof", "view", "Payments") is False

    def test_prof_cannot_access_dues(self):
        assert can("Prof", "view", "Dues") is False

    def test_teacher_alias_resolves_correctly(self):
        # "Teacher" alias doit se comporter comme "Prof"
        assert can("Teacher", "update", "Grades") == "conditional"
        assert can("Teacher", "delete", "Students") is False

    def test_prof_attendance_is_conditional(self):
        assert can("Prof", "create", "Attendance") == "conditional"


# ─────────────────────────────────────────────────────────────────────────────
# can() — Secretaire / Staff alias
# ─────────────────────────────────────────────────────────────────────────────
class TestSecretairePermissions:
    def test_secretaire_can_create_students(self):
        assert can("Secretaire", "create", "Students") is True

    def test_secretaire_cannot_view_payments(self):
        assert can("Secretaire", "view", "Payments") is False

    def test_secretaire_cannot_view_dues(self):
        assert can("Secretaire", "view", "Dues") is False

    def test_staff_alias_cannot_view_payments(self):
        assert can("Staff", "view", "Payments") is False

    def test_staff_alias_can_create_students(self):
        assert can("Staff", "create", "Students") is True


# ─────────────────────────────────────────────────────────────────────────────
# can() — parent
# ─────────────────────────────────────────────────────────────────────────────
class TestParentPermissions:
    def test_parent_can_view_own_student_conditionally(self):
        assert can("parent", "view", "Students") == "conditional"

    def test_parent_cannot_update_grades(self):
        assert can("parent", "update", "Grades") is False

    def test_parent_cannot_view_payments(self):
        assert can("parent", "view", "Payments") is False

    def test_parent_can_view_dues_conditionally(self):
        assert can("parent", "view", "Dues") == "conditional"


# ─────────────────────────────────────────────────────────────────────────────
# can() — Rôle inconnu
# ─────────────────────────────────────────────────────────────────────────────
class TestUnknownRole:
    def test_unknown_role_always_false(self):
        assert can("Ghost", "view", "Students") is False

    def test_unknown_resource_always_false(self):
        assert can("Admin", "view", "NonExistentResource") is False


# ─────────────────────────────────────────────────────────────────────────────
# is_allowed() — traite conditional comme True
# ─────────────────────────────────────────────────────────────────────────────
class TestIsAllowed:
    def test_conditional_counts_as_allowed(self):
        assert is_allowed("Prof", "view", "Grades") is True

    def test_false_is_not_allowed(self):
        assert is_allowed("Prof", "delete", "Students") is False

    def test_true_is_allowed(self):
        assert is_allowed("Admin", "delete", "Students") is True


# ─────────────────────────────────────────────────────────────────────────────
# get_allowed_resources()
# ─────────────────────────────────────────────────────────────────────────────
class TestGetAllowedResources:
    def test_comptable_can_view_financial_resources(self):
        resources = get_allowed_resources("Comptable", "view")
        assert "Payments" in resources
        assert "Dues" in resources
        assert "Expenses" in resources
        assert "Grades" not in resources

    def test_prof_update_resources_are_conditional_only(self):
        resources = get_allowed_resources("Prof", "update")
        assert "Grades" in resources
        assert "Students" not in resources  # Prof cannot update Students

    def test_unknown_role_returns_empty(self):
        assert get_allowed_resources("Ghost", "view") == []
