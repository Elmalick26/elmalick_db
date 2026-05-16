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

import logging
import os
import sys
import time

# ضمان أن الاستيرادات تجد وحدات المشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.auth import router as auth_router
from api.limiter import limiter
from api.routes_parent import router as parent_router
from api.routes_students import router as students_router

_req_logger = logging.getLogger("api.requests")

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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

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
# v1 (current stable) — canonical versioned routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(students_router, prefix="/api/v1")
app.include_router(parent_router, prefix="/api/v1")

# Legacy unversioned routes — kept for backward compatibility
# Responses include a Deprecation header to signal migration path.
app.include_router(auth_router, prefix="/api", include_in_schema=False)
app.include_router(students_router, prefix="/api", include_in_schema=False)
app.include_router(parent_router, prefix="/api", include_in_schema=False)


# ──────────────────────────────────────────── Deprecation middleware
@app.middleware("http")
async def add_deprecation_header(request: Request, call_next):
    """Add Deprecation header on legacy /api/* routes (not /api/v1/ or /api/docs etc.)."""
    response = await call_next(request)
    path = request.url.path
    # Only flag the old unversioned API paths (not v1, not system endpoints)
    if (
        path.startswith("/api/")
        and not path.startswith("/api/v1/")
        and not path.startswith("/api/docs")
        and not path.startswith("/api/redoc")
        and not path.startswith("/api/openapi")
        and path not in ("/api/health", "/api/")
    ):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Sat, 01 Jan 2027 00:00:00 GMT"
        response.headers["Link"] = f'<{path.replace("/api/", "/api/v1/", 1)}>; rel="successor-version"'
    return response


# ──────────────────────────────────────────── Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every API request: method, path, status_code, duration_ms, user_id.

    • Skips /api/health to avoid log noise.
    • Emits WARNING level for requests that take longer than 2 000 ms.
    """
    path = request.url.path

    # Skip health-check endpoint
    if path in ("/api/health", "/api/v1/health"):
        return await call_next(request)

    t0 = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - t0) * 1000, 1)

    # Extract user identity from Bearer JWT (silently — never raises)
    user_id: str | None = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from api.auth import extract_token_subject

        user_id = extract_token_subject(auth_header[7:])

    log_msg = f"{request.method} {path} {response.status_code} " f"{duration_ms}ms user={user_id}"
    if duration_ms > 2000:
        _req_logger.warning("SLOW REQUEST \u2014 %s", log_msg)
    else:
        _req_logger.info(log_msg)

    return response


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
    """Vérification de l'état de l'API: DB connectivity, latence, taille, dernier backup."""
    import glob
    import os

    try:
        from database_setup import DatabaseManager

        db = DatabaseManager()
        t0 = time.perf_counter()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.execute("SELECT COUNT(*) FROM information_schema.tables " "WHERE table_schema = 'public'")
            row = cur.fetchone()
            table_count: int = row[0] if row else 0
            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            size_row = cur.fetchone()
            db_size: str = size_row[0] if size_row else "unknown"
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        # آخر backup: أحدث ملف في مجلد backups/
        from config_manager import ConfigManager

        backup_dir = ConfigManager().backup_dir
        backup_files = sorted(glob.glob(os.path.join(backup_dir, "*.sql")))
        last_backup = os.path.basename(backup_files[-1]) if backup_files else None

        return {
            "status": "ok",
            "database": "connected",
            "db_latency_ms": db_latency_ms,
            "table_count": table_count,
            "db_size": db_size,
            "last_backup": last_backup,
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "database": str(e)})


@app.get("/api/v1/health", tags=["System"], summary="État du serveur (v1)")
async def health_v1():
    """Alias v1 du health check — même réponse que /api/health."""
    return await health()


@app.get("/api", tags=["System"], include_in_schema=False)
async def root():
    return {"name": "El Malick Gest API", "version": "1.0.0", "docs": "/api/docs"}
