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

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from database_setup import DatabaseManager
from app_logger import AppLogger
from api.auth import get_current_user, require_role, TokenData

router = APIRouter(prefix="/students", tags=["Students"])

_ALLOWED = require_role("Admin", "Teacher", "Staff")


# ──────────────────────────────────────────── helpers
def _get_active_year(conn) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("SELECT id FROM AcademicYears WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None


# ──────────────────────────────────────────── routes
@router.get("/", summary="Liste des élèves")
async def list_students(
    q: Optional[str] = Query(None, description="Recherche par nom"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: TokenData = Depends(_ALLOWED)
):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            year_id = _get_active_year(conn)
            offset = (page - 1) * page_size
            cur = conn.cursor()

            if q:
                pat = f"%{q}%"
                cur.execute("""
                    SELECT S.id, S.first_name_fr, S.last_name_fr,
                           S.first_name_ar, S.last_name_ar,
                           S.gender, S.birth_date, S.status,
                           C.class_name_fr AS class_name
                    FROM Students S
                    LEFT JOIN StudentClassNumbers SCN
                          ON S.id = SCN.student_id AND SCN.year_id = %s
                    LEFT JOIN Classes C ON SCN.class_id = C.id
                    WHERE S.status != 'Archived'
                      AND (S.first_name_fr ILIKE %s OR S.last_name_fr ILIKE %s
                           OR S.first_name_ar ILIKE %s OR S.last_name_ar ILIKE %s)
                    ORDER BY S.last_name_fr, S.first_name_fr
                    LIMIT %s OFFSET %s
                """, (year_id, pat, pat, pat, pat, page_size, offset))
            else:
                cur.execute("""
                    SELECT S.id, S.first_name_fr, S.last_name_fr,
                           S.first_name_ar, S.last_name_ar,
                           S.gender, S.birth_date, S.status,
                           C.class_name_fr AS class_name
                    FROM Students S
                    LEFT JOIN StudentClassNumbers SCN
                          ON S.id = SCN.student_id AND SCN.year_id = %s
                    LEFT JOIN Classes C ON SCN.class_id = C.id
                    WHERE S.status != 'Archived'
                    ORDER BY S.last_name_fr, S.first_name_fr
                    LIMIT %s OFFSET %s
                """, (year_id, page_size, offset))

            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]

            # إجمالي العدد
            cur.execute("SELECT COUNT(*) FROM Students WHERE status != 'Archived'")
            total = cur.fetchone()[0]

        return {"total": total, "page": page, "page_size": page_size, "data": rows}

    except Exception as e:
        AppLogger.error("API.Students", f"list_students error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}", summary="Détails d'un élève")
async def get_student(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Students WHERE id = %s", (student_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Élève introuvable")
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
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
            year_id = _get_active_year(conn)
            cur = conn.cursor()
            cur.execute("""
                SELECT G.score,
                       SB.subject_name_fr AS subject,
                       SB.coefficient,
                       AP.period_name_fr AS period,
                       AT.name_fr AS exam_type,
                       CASE WHEN LOWER(CY.name_fr) SIMILAR TO '%%(elem|prim|ibtida)%%'
                            THEN 10.0 ELSE 20.0 END AS max_score
                FROM Grades G
                JOIN Subjects SB ON G.subject_id = SB.id
                JOIN AssessmentTypes AT ON G.assessment_id = AT.id
                JOIN AcademicPeriods AP ON AT.period_id = AP.id
                JOIN StudentClassNumbers SCN ON G.student_id = SCN.student_id AND SCN.year_id = G.year_id
                JOIN Classes CL ON SCN.class_id = CL.id
                JOIN Cycles CY ON CL.cycle_id = CY.id
                WHERE G.student_id = %s AND G.year_id = %s
                ORDER BY AP.sort_order, SB.subject_name_fr
            """, (student_id, year_id))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        AppLogger.error("API.Students", f"get_student_grades({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}/attendance", summary="Présences de l'élève")
async def get_student_attendance(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            year_id = _get_active_year(conn)
            cur = conn.cursor()
            cur.execute("""
                SELECT date, status, reason
                FROM StudentAttendance
                WHERE student_id = %s AND year_id = %s
                ORDER BY date DESC
                LIMIT 90
            """, (student_id, year_id))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        AppLogger.error("API.Students", f"get_student_attendance({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/{student_id}/dues", summary="Frais scolaires de l'élève")
async def get_student_dues(student_id: int, current: TokenData = Depends(_ALLOWED)):
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            year_id = _get_active_year(conn)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, label, amount, due_date, is_paid
                FROM StudentDues
                WHERE student_id = %s AND year_id = %s
                ORDER BY due_date
            """, (student_id, year_id))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        AppLogger.error("API.Students", f"get_student_dues({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")
