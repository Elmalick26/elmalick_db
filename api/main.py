"""
api/main.py — نقطة دخول REST API لـ El Malick Gest

تشغيل:
    # من مجلد المشروع:
    .venv\\Scripts\\uvicorn.exe api.main:app --reload --port 8000

وثائق تفاعلية:
    http://localhost:8000/api/docs
    http://localhost:8000/api/redoc
"""

from __future__ import annotations

import os, sys
# ضمان أن الاستيرادات تجد وحدات المشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.auth import router as auth_router
from api.routes_students import router as students_router
from api.routes_parent import router as parent_router
from api.limiter import limiter

# ──────────────────────────────────────────── App
app = FastAPI(
    title="El Malick Gest API",
    description=(
        "API REST pour le système de gestion scolaire El Malick Gest.\n\n"
        "**Authentification**: JWT Bearer (obtenir via POST /api/auth/token).\n\n"
        "**Portail parents**: accès limité via POST /api/parent/login avec le code élève + PIN."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ──────────────────────────────────────────── Rate Limiter state + handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ──────────────────────────────────────────── CORS
# En production: remplacer ["*"] par les domaines autorisés
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────── Routers
app.include_router(auth_router,     prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(parent_router,   prefix="/api")

# ──────────────────────────────────────────── Static files (Parent Portal)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ──────────────────────────────────────────── Parent Portal entry point
@app.get("/portal", include_in_schema=False, summary="Portail parents")
async def parent_portal():
    """Sert l'interface HTML du portail parents."""
    index = os.path.join(_static_dir, "parent", "index.html")
    return FileResponse(index, media_type="text/html")


# ──────────────────────────────────────────── Health check
@app.get("/api/health", tags=["System"], summary="État du serveur")
async def health():
    """Vérification rapide que l'API fonctionne."""
    try:
        from database_setup import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            conn.cursor().execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": str(e)}
        )


@app.get("/api", tags=["System"], include_in_schema=False)
async def root():
    return {"name": "El Malick Gest API", "version": "1.0.0", "docs": "/api/docs"}
