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

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import timedelta
from typing import Optional

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from api.auth import ALGORITHM, SECRET_KEY, create_access_token, get_current_user, require_role
from api.limiter import limiter
from app_logger import AppLogger
from database_setup import DatabaseManager, log_audit
from error_codes import DB_QUERY
from repositories.parent_repo import ParentRepository

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
    student_code: str  # رمز الطالب الثابت (EMG-XXXX) أو الرقم القديم كانتقال
    pin: str  # رمز PIN (4-6 أرقام)


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
@limiter.limit("10/minute")
async def parent_login(request: Request, data: ParentLoginRequest):
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
            repo = ParentRepository(conn)
            code = data.student_code.strip().upper()

            row = repo.get_student_for_parent_login(code)

            if not row:
                AppLogger.warning("API.Parent", f"parent_login échoué — code introuvable: {data.student_code}")
                raise HTTPException(
                    status_code=404, detail=f"Code élève '{code}' introuvable. Vérifiez le code sur le carnet scolaire."
                )

            s_id, fn, ln, p_name, p_phone, pin_hash, pin_plain, scode = row

            if pin_hash:
                # ── Cas normal : PIN hashé présent
                if not _verify_pin(data.pin, pin_hash):
                    AppLogger.warning("API.Parent", f"parent_login PIN incorrect — élève {s_id} ({scode})")
                    raise HTTPException(status_code=401, detail="PIN incorrect.")
            elif pin_plain:
                # ── Cas de migration : ancien PIN en texte clair → comparer puis upgrader
                if data.pin != pin_plain:
                    AppLogger.warning("API.Parent", f"parent_login PIN incorrect (migration) — élève {s_id}")
                    raise HTTPException(status_code=401, detail="PIN incorrect.")
                # Mise à niveau vers bcrypt
                new_hash = _hash_pin(data.pin)
                repo.update_student_pin(s_id, new_hash)
                conn.commit()
                AppLogger.info("API.Parent", f"PIN migré vers bcrypt — élève {s_id}")
            else:
                # ── Premier accès : aucun PIN défini
                if len(data.pin) < 4 or not data.pin.isdigit():
                    raise HTTPException(status_code=400, detail="Le PIN doit contenir au moins 4 chiffres.")
                new_hash = _hash_pin(data.pin)
                repo.update_student_pin(s_id, new_hash)
                conn.commit()
                AppLogger.info("API.Parent", f"Premier accès — PIN défini pour élève {s_id} ({fn} {ln})")

            token = create_access_token(
                {"student_id": s_id, "role": "parent"}, expires_delta=timedelta(minutes=PARENT_TOKEN_EXPIRE_MINUTES)
            )
            AppLogger.info("API.Parent", f"Connexion réussie — {scode} ({fn} {ln})")
            log_audit(conn, actor=f"parent:{scode}", action="LOGIN", target=f"student_id={s_id}")
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
        raise HTTPException(status_code=500, detail={"message": "Erreur serveur", "error_code": DB_QUERY})


@router.get("/me", summary="Infos de l'élève (parent)")
async def parent_me(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = ParentRepository(conn)
            year_id = repo.get_active_year_id()
            if year_id is None:
                raise HTTPException(status_code=503, detail="Aucune année scolaire active")
            result = repo.get_student_info(student_id, year_id)
            if not result:
                raise HTTPException(status_code=404, detail="Élève introuvable")
            return result
    except HTTPException:
        raise
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_me({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail={"message": "Erreur serveur", "error_code": DB_QUERY})


@router.get("/grades", summary="Notes (parent)")
async def parent_grades(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            repo = ParentRepository(conn)
            year_id = repo.get_active_year_id()
            if not year_id:
                return []
            return repo.get_student_grades(student_id, year_id)
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_grades({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail={"message": "Erreur serveur", "error_code": DB_QUERY})


@router.get("/attendance", summary="Présences (parent)")
async def parent_attendance(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            return ParentRepository(conn).get_student_attendance(student_id)
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_attendance({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail={"message": "Erreur serveur", "error_code": DB_QUERY})


@router.get("/dues", summary="Frais scolaires (parent)")
async def parent_dues(parent: dict = Depends(get_current_parent)):
    student_id = parent["student_id"]
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            return ParentRepository(conn).get_student_dues(student_id)
    except Exception as e:
        AppLogger.error("API.Parent", f"parent_dues({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail={"message": "Erreur serveur", "error_code": DB_QUERY})


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
            repo = ParentRepository(conn)
            if not repo.check_student_active(student_id):
                raise HTTPException(status_code=404, detail="Élève introuvable")
            repo.reset_student_pin(student_id)
            conn.commit()
            log_audit(conn, actor=current_user.username, action="RESET_PARENT_PIN", target=f"student_id={student_id}")
            AppLogger.info("API.Parent", f"PIN parent réinitialisé — élève {student_id} par {current_user.username}")
            return {
                "detail": f"PIN réinitialisé pour l'élève {student_id}. Le parent pourra définir un nouveau PIN à la prochaine connexion."
            }
    except HTTPException:
        raise
    except Exception as e:
        AppLogger.error("API.Parent", f"reset_parent_pin({student_id}) error: {e}")
        raise HTTPException(status_code=500, detail="Erreur serveur")
