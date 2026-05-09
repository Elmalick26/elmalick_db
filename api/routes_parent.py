"""
api/routes_parent.py — بوابة أولياء الأمور (Phase 5.2 → 6.3)

• POST /api/parent/login  ← دخول بـ (student_code + PIN)
• GET  /api/parent/me     ← بيانات الطالب
• GET  /api/parent/grades ← الدرجات
• GET  /api/parent/attendance ← الحضور
• GET  /api/parent/dues   ← المستحقات

المصادقة: JWT مستقل — parent_token يحتوي student_id فقط.
student_code: معرف ثابت وفريد للطالب (EMG-XXXX) لا يتغير عبر السنوات.
PIN مشفر بـ bcrypt في parent_pin_hash؛ ترقية تلقائية من parent_pin النصي القديم.
"""

from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import bcrypt as _bcrypt
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt

from database_setup import DatabaseManager
from app_logger import AppLogger
from api.auth import SECRET_KEY, ALGORITHM, create_access_token, require_role, get_current_user

router = APIRouter(prefix="/parent", tags=["Parent Portal"])
_parent_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/parent/login")

PARENT_TOKEN_EXPIRE_MINUTES = 120


# ──────────────────────── PIN helpers (bcrypt)
def _hash_pin(pin: str) -> str:
    return _bcrypt.hashpw(pin.encode(), _bcrypt.gensalt(rounds=10)).decode()

def _verify_pin(pin: str, stored_hash: str) -> bool:
    try:
        return _bcrypt.checkpw(pin.encode(), stored_hash.encode())
    except Exception:
        return False


# ──────────────────────── Schemas
class ParentLoginRequest(BaseModel):
    student_code: str   # رمز الطالب الثابت (EMG-XXXX) أو الرقم القديم كانتقال
    pin: str            # رمز PIN (4-6 أرقام)


# ──────────────────────── Helpers
def _get_active_year(conn) -> Optional[int]:
    cur = conn.cursor()
    cur.execute("SELECT id FROM AcademicYears WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None


# ──────────────────────── Dependency
async def get_current_parent(token: str = Depends(_parent_oauth2)) -> dict:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token parent invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id = payload.get("student_id")
        role = payload.get("role")
        if student_id is None or role != "parent":
            raise exc
        return {"student_id": student_id}
    except JWTError:
        raise exc


# ──────────────────────── Routes
@router.post("/login", summary="Connexion parent")
async def parent_login(data: ParentLoginRequest):
    """
    Authentification via le code permanent de l'élève (Students.student_code) + PIN.
    - student_code : identifiant fixe EMG-XXXX, invariant d'une année à l'autre.
    - PIN           : 4-6 chiffres. Stocké hashé (bcrypt). Rétro-compatible avec
                      l'ancienne colonne parent_pin (texte clair) — mise à niveau
                      automatique à la première connexion.
    - Premier accès (aucun hash ni ancien PIN) : tout PIN ≥ 4 chiffres est accepté
      et enregistré hashé.
    """
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            code = data.student_code.strip().upper()

            cur.execute("""
                SELECT id, first_name_fr, last_name_fr,
                       parent_name, parent_phone,
                       COALESCE(parent_pin_hash, '') AS pin_hash,
                       COALESCE(parent_pin, '')      AS pin_plain,
                       student_code
                FROM Students
                WHERE student_code = %s
                  AND status != 'Archived'
                LIMIT 1
            """, (code,))
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"Code élève '{code}' introuvable. Vérifiez le code sur le carnet scolaire.")

            s_id, fn, ln, p_name, p_phone, pin_hash, pin_plain, scode = row

            if pin_hash:
                # ── Cas normal : PIN hashé présent
                if not _verify_pin(data.pin, pin_hash):
                    raise HTTPException(status_code=401, detail="PIN incorrect.")
            elif pin_plain:
                # ── Cas de migration : ancien PIN en texte clair → comparer puis upgrader
                if data.pin != pin_plain:
                    raise HTTPException(status_code=401, detail="PIN incorrect.")
                # Mise à niveau vers bcrypt
                new_hash = _hash_pin(data.pin)
                cur.execute(
                    "UPDATE Students SET parent_pin_hash = %s, parent_pin = NULL WHERE id = %s",
                    (new_hash, s_id)
                )
                conn.commit()
                AppLogger.info("API.Parent", f"PIN migré vers bcrypt — élève {s_id}")
            else:
                # ── Premier accès : aucun PIN défini
                if len(data.pin) < 4 or not data.pin.isdigit():
                    raise HTTPException(status_code=400, detail="Le PIN doit contenir au moins 4 chiffres.")
                new_hash = _hash_pin(data.pin)
                cur.execute(
                    "UPDATE Students SET parent_pin_hash = %s, parent_pin = NULL WHERE id = %s",
                    (new_hash, s_id)
                )
                conn.commit()
                AppLogger.info("API.Parent", f"Premier accès — PIN défini pour élève {s_id} ({fn} {ln})")

            token = create_access_token(
                {"student_id": s_id, "role": "parent"},
                expires_delta=timedelta(minutes=PARENT_TOKEN_EXPIRE_MINUTES)
            )
            AppLogger.info("API.Parent", f"Connexion réussie — {scode} ({fn} {ln})")
            return {
                "access_token": token,
                "token_type": "bearer",
                "student_name": f"{fn} {ln}",
                "parent_name": p_name or "",
                "student_code": scode,
            }

    except HTTPException:
        raise
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_login error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/me", summary="Infos de l'élève (parent)")
async def parent_me(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT S.first_name_fr, S.last_name_fr,
                       S.first_name_ar, S.last_name_ar,
                       S.birth_date, S.gender,
                       S.parent_name, S.parent_phone, S.parent_email,
                       C.class_name_fr AS class_name,
                       AY.year_label AS academic_year
                FROM Students S
                LEFT JOIN StudentClassNumbers SCN ON S.id = SCN.student_id 
                    AND SCN.year_id = (SELECT id FROM AcademicYears WHERE is_active = 1 LIMIT 1)
                LEFT JOIN AcademicYears AY ON SCN.year_id = AY.id AND AY.is_active = 1
                LEFT JOIN Classes C ON SCN.class_id = C.id
                WHERE S.id = %s
            """, (student_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Élève introuvable")
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    except HTTPException:
        raise
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_me({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/grades", summary="Notes (parent)")
async def parent_grades(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            year_id = _get_active_year(conn)
            if not year_id:
                return []
            
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
        AppLogger.error("API.Parent", f"parent_grades({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/attendance", summary="Présences (parent)")
async def parent_attendance(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT SA.date, SA.status, SA.reason
                FROM StudentAttendance SA
                JOIN AcademicYears AY ON SA.year_id = AY.id AND AY.is_active = 1
                WHERE SA.student_id = %s
                ORDER BY SA.date DESC
                LIMIT 60
            """, (student_id,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_attendance({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


@router.get("/dues", summary="Frais scolaires (parent)")
async def parent_dues(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT SD.fee_description AS label,
                       SD.net_amount AS amount,
                       SD.due_date,
                       SD.is_paid
                FROM StudentDues SD
                JOIN AcademicYears AY ON SD.year_id = AY.id AND AY.is_active = 1
                WHERE SD.student_id = %s
                ORDER BY SD.due_date
            """, (student_id,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_dues({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")


# ──────────────────────── Admin: Réinitialiser le PIN parent
@router.post("/reset-pin/{student_id}", summary="Réinitialiser PIN parent (Admin)")
async def reset_parent_pin(
    student_id: int,
    current_user=Depends(require_role("Admin", "Staff")),
):
    """
    Réinitialise le PIN parent d'un élève à NULL (le parent pourra le redéfinir lors du prochain accès).
    Réservé aux rôles Admin et Staff.
    """
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Students WHERE id = %s AND status != 'Archived'", (student_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Élève introuvable")
            cur.execute(
                "UPDATE Students SET parent_pin_hash = NULL, parent_pin = NULL WHERE id = %s",
                (student_id,)
            )
            conn.commit()
            AppLogger.info("API.Parent", f"PIN parent réinitialisé — élève {student_id} par {current_user.username}")
            return {"detail": f"PIN réinitialisé pour l'élève {student_id}. Le parent pourra définir un nouveau PIN à la prochaine connexion."}
    except HTTPException:
        raise
    except Exception as e:
        AppLogger.error("API.Parent", f"reset_parent_pin({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")
