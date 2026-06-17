"""RBAC Permission Checker — services/authorization.py

Mots clés: T5.2 RBAC Matrix v1 + T5.3 PermissionChecker

Rôles canoniques (correspondant à Users.role en base):
    Admin | Comptable | Secretaire | Pédagogique | Prof | parent

Alias API (pour la compatibilité avec les JWT existants qui utilisent
"Teacher" et "Staff"):
    Teacher → Prof
    Staff   → Secretaire

Actions:
    view | create | update | delete | export | approve | reset

Ressources:
    Students | Staff | Grades | Attendance | Payments | Expenses
    Users | AuditLogs | Reports | Settings | Backup | Discipline | Dues
    Inventory | Communication | Timetable | Bulletins | AcademicSettings

Permissions conditionnelles:
    Certaines cellules ont la valeur "own_class" (Prof ne voit que sa classe)
    ou "own_student" (parent ne voit que son propre enfant).
    La vérification de la condition est à la charge du code appelant.
    can() renvoie "conditional" pour ces cas.
"""

from __future__ import annotations

from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# Alias : rôles API → rôles canoniques
# ─────────────────────────────────────────────────────────────────────────────
_ROLE_ALIASES: dict[str, str] = {
    "Teacher": "Prof",
    "Staff": "Secretaire",
}


def canonical_role(role: str) -> str:
    """Normalise un alias API vers le rôle canonique."""
    return _ROLE_ALIASES.get(role, role)


# ─────────────────────────────────────────────────────────────────────────────
# RBAC Matrix v1
# Structure: {role: {resource: {action: bool | "conditional"}}}
# ─────────────────────────────────────────────────────────────────────────────
PermValue = Literal[True, False, "conditional"]

RBAC_MATRIX: dict[str, dict[str, dict[str, PermValue]]] = {
    # ── Admin : accès total ─────────────────────────────────────────────────
    "Admin": {
        "Students": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": True,
            "reset": True,
        },
        "Staff": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": True,
            "reset": True,
        },
        "Grades": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": True,
            "reset": False,
        },
        "Attendance": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Payments": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": True,
            "reset": False,
        },
        "Expenses": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": True,
            "reset": False,
        },
        "Dues": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": True,
            "reset": False,
        },
        "Users": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": False,
            "approve": True,
            "reset": True,
        },
        "AuditLogs": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Reports": {
            "view": True,
            "create": True,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Settings": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": False,
            "approve": False,
            "reset": True,
        },
        "Backup": {
            "view": True,
            "create": True,
            "update": False,
            "delete": True,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Discipline": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Inventory": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Communication": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Timetable": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Bulletins": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": True,
            "reset": False,
        },
        "AcademicSettings": {
            "view": True,
            "create": True,
            "update": True,
            "delete": True,
            "export": False,
            "approve": False,
            "reset": False,
        },
    },
    # ── Comptable : finances uniquement ────────────────────────────────────
    "Comptable": {
        "Students": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Staff": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Grades": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Attendance": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Payments": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Expenses": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Dues": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Users": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AuditLogs": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Reports": {
            "view": True,
            "create": True,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Settings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Backup": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Discipline": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Inventory": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Communication": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Timetable": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Bulletins": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AcademicSettings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
    },
    # ── Secretaire : administration scolaire ───────────────────────────────
    "Secretaire": {
        "Students": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Staff": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Grades": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Attendance": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Payments": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Expenses": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Dues": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Users": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AuditLogs": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Reports": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Settings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Backup": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Discipline": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Inventory": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Communication": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Timetable": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Bulletins": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AcademicSettings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
    },
    # ── Pédagogique : responsable pédagogique (toutes les classes) ─────────
    "Pédagogique": {
        "Students": {
            "view": True,
            "create": False,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Staff": {
            "view": True,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Grades": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": True,
            "reset": False,
        },
        "Attendance": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Payments": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Expenses": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Dues": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Users": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AuditLogs": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Reports": {
            "view": True,
            "create": True,
            "update": False,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Settings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Backup": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Discipline": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Inventory": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Communication": {
            "view": True,
            "create": True,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Timetable": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "Bulletins": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": True,
            "approve": False,
            "reset": False,
        },
        "AcademicSettings": {
            "view": True,
            "create": True,
            "update": True,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
    },
    # ── Prof : enseignant (sa classe uniquement — conditional) ─────────────
    "Prof": {
        "Students": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Staff": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Grades": {
            "view": "conditional",
            "create": "conditional",
            "update": "conditional",
            "delete": False,
            "export": "conditional",
            "approve": False,
            "reset": False,
        },
        "Attendance": {
            "view": "conditional",
            "create": "conditional",
            "update": "conditional",
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Payments": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Expenses": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Dues": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Users": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AuditLogs": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Reports": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Settings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Backup": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Discipline": {
            "view": "conditional",
            "create": "conditional",
            "update": "conditional",
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Inventory": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Communication": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Timetable": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Bulletins": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AcademicSettings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
    },
    # ── parent : portail parents (son enfant uniquement) ───────────────────
    "parent": {
        "Students": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Staff": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Grades": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Attendance": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Payments": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Expenses": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Dues": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Users": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "AuditLogs": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Reports": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Settings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Backup": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Discipline": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Inventory": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Communication": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Timetable": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
        "Bulletins": {
            "view": "conditional",
            "create": False,
            "update": False,
            "delete": False,
            "export": "conditional",
            "approve": False,
            "reset": False,
        },
        "AcademicSettings": {
            "view": False,
            "create": False,
            "update": False,
            "delete": False,
            "export": False,
            "approve": False,
            "reset": False,
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def can(role: str, action: str, resource: str) -> PermValue:
    """Vérifie si un rôle peut effectuer une action sur une ressource.

    Retourne:
        True          — autorisé sans condition
        False         — refusé
        "conditional" — autorisé sous condition (vérification scope à la charge de l'appelant)

    Exemples:
        can("Prof", "update", "Grades")     → "conditional"
        can("Comptable", "view", "Dues")    → True
        can("Prof", "delete", "Students")   → False
        can("Teacher", "view", "Students")  → "conditional"  (alias → Prof)
    """
    role = canonical_role(role)
    role_perms = RBAC_MATRIX.get(role)
    if role_perms is None:
        return False
    resource_perms = role_perms.get(resource)
    if resource_perms is None:
        return False
    return resource_perms.get(action, False)


def is_allowed(role: str, action: str, resource: str) -> bool:
    """Comme can() mais traite 'conditional' comme True.

    Utile pour les vérifications rapides où la condition de scope
    est gérée séparément (ex: filtre SQL après validation initiale).
    """
    result = can(role, action, resource)
    return result is True or result == "conditional"


def get_allowed_resources(role: str, action: str) -> list[str]:
    """Renvoie la liste des ressources pour lesquelles le rôle peut effectuer l'action."""
    role = canonical_role(role)
    role_perms = RBAC_MATRIX.get(role, {})
    return [resource for resource, actions in role_perms.items() if actions.get(action, False) is not False]
