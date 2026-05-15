"""
api/routes_students.py — مسارات بيانات الطلاب

GET  /api/students/                → قائمة الطلاب (مع بحث + pagination)
GET  /api/students/{id}            → تفاصيل طالب واحد
GET  /api/students/{id}/grades     → درجات الطالب في السنة الحالية
GET  /api/students/{id}/attendance → حضور الطالب في السنة الحالية
GET  /api/students/{id}/dues       → مستحقات الطالب

الوصول: Admin, Teacher, Staff — أما Parent فيصل فقط لبياناته عبر /parent
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from database_setup import DatabaseManager
from app_logger import AppLogger
from api.auth import get_current_user, require_role, TokenData
from repositories.students_api_repo import StudentsApiRepository

router = APIRouter(prefix="/students", tags=["Students"])

_ALLOWED = require_role("Admin", "Teacher", "Staff")


# ──────────────────────────────────────────── routes
@router.get("/", summary="Liste des élèves")
async def list_students(
    q: Optional[str] = Query(None, description="Recherche par nom"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: TokenData = Depends(_ALLOWED),
):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentsApiRepository(conn)
            year_id = repo.get_active_year_id()
            offset = (page - 1) * page_size
            rows = repo.list_students(year_id, q, page_size, offset)
            total = repo.count_students()
        return {"total": total, "page": page, "page_size": page_size, "data": rows}
    except Exception as e:
        AppLogger.error("API.Students", f"list_students error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}", summary="Détails d'un élève")
async def get_student(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            row = StudentsApiRepository(conn).get_student_by_id(student_id)
            if not row:
                raise HTTPException(status_code=404, detail="Élève introuvable")
            return row
    except HTTPException:
        raise
    except Exception as e:
        AppLogger.error("API.Students", f"get_student({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}/grades", summary="Notes de l'élève")
async def get_student_grades(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentsApiRepository(conn)
            year_id = repo.get_active_year_id()
            return repo.get_grades(student_id, year_id)
    except Exception as e:
        AppLogger.error("API.Students", f"get_student_grades({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}/attendance", summary="Présences de l'élève")
async def get_student_attendance(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentsApiRepository(conn)
            year_id = repo.get_active_year_id()
            return repo.get_attendance(student_id, year_id)
    except Exception as e:
        AppLogger.error("API.Students", f"get_student_attendance({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}/dues", summary="Frais scolaires de l'élève")
async def get_student_dues(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = StudentsApiRepository(conn)
            year_id = repo.get_active_year_id()
            return repo.get_dues(student_id, year_id)
    except Exception as e:
        AppLogger.error("API.Students", f"get_student_dues({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")
