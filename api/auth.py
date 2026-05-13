"""
api/auth.py — نظام المصادقة عبر JWT لـ FastAPI

• POST /api/auth/token  ← تسجيل الدخول (username + password)
• كل نقطة محمية تطلب Header: Authorization: Bearer <token>

الخوارزمية: HS256 — SECRET_KEY من متغير البيئة ELMALICK_API_SECRET
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database_setup import DatabaseManager
from app_logger import AppLogger

# ────────────────────────────────────────── config
SECRET_KEY: str = os.environ.get("ELMALICK_API_SECRET", "change-me-in-production-!!!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# ────────────────────────────────────────── Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ────────────────────────────────────────── Helpers
def _verify_user(username: str, password: str) -> Optional[dict]:
    """
    التحقق من بيانات المستخدم مقابل جدول Users.
    يعيد dict(id, username, role) أو None.
    """
    try:
        import bcrypt as _bcrypt
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, role FROM Users WHERE username = %s",
                (username,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            uid, uname, pw_hash, role = row
            if isinstance(pw_hash, str):
                pw_hash = pw_hash.encode()
            if _bcrypt.checkpw(password.encode(), pw_hash):
                return {"id": uid, "username": uname, "role": role}
    except Exception as e:
        AppLogger.error("API.Auth", f"verify_user error: {e}")
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception


def require_role(*allowed_roles: str):
    """Dependency factory — vérifie que le rôle de l'utilisateur est autorisé."""
    async def _checker(current: TokenData = Depends(get_current_user)) -> TokenData:
        if current.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle '{current.role}' non autorisé pour cette ressource"
            )
        return current
    return _checker


# ────────────────────────────────────────── Routes
@router.post("/token", response_model=Token, summary="Obtenir un token JWT")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = _verify_user(form_data.username, form_data.password)
    if not user:
        AppLogger.warning("API.Auth", f"Tentative de connexion échouée: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    AppLogger.info("API.Auth", f"Connexion API réussie: {user['username']} ({user['role']})")
    return Token(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        username=user["username"]
    )
