"""
smoke_tests.py — اختبارات الدخان بعد النشر مباشرة

التشغيل (بعد رفع الخادم):
    python smoke_tests.py
    python smoke_tests.py --url http://prod-server:8000
    python smoke_tests.py --url http://localhost:8000 --user admin --password admin

يخرج بـ exit code 0 إذا نجحت كل الاختبارات، و1 إذا فشل أي منها.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

# ── httpx أو requests — الاثنان مقبولان ─────────────────────────────────
try:
    import httpx as _http_lib  # type: ignore

    def _get(url: str, headers: dict | None = None, timeout: float = 10.0):
        return httpx.get(url, headers=headers or {}, timeout=timeout)  # type: ignore

    def _post(
        url: str,
        data: dict | None = None,
        json_body: dict | None = None,
        headers: dict | None = None,
        timeout: float = 10.0,
    ):
        return httpx.post(url, data=data, json=json_body, headers=headers or {}, timeout=timeout)  # type: ignore

    import httpx  # noqa: F401  (imported for side-effect above)

except ImportError:
    import requests as _http_lib  # type: ignore

    def _get(url: str, headers: dict | None = None, timeout: float = 10.0):
        return _http_lib.get(url, headers=headers or {}, timeout=timeout)

    def _post(
        url: str,
        data: dict | None = None,
        json_body: dict | None = None,
        headers: dict | None = None,
        timeout: float = 10.0,
    ):
        return _http_lib.post(url, data=data, json=json_body, headers=headers or {}, timeout=timeout)


# ── helpers ──────────────────────────────────────────────────────────────

_PASS = "✅ PASS"
_FAIL = "❌ FAIL"
_results: list[dict[str, Any]] = []


def _check(name: str, condition: bool, detail: str = "") -> bool:
    status = _PASS if condition else _FAIL
    _results.append({"name": name, "passed": condition, "detail": detail})
    pad = " " * max(0, 50 - len(name))
    print(f"  {status}  {name}{pad}{detail}")
    return condition


def _section(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 60 - len(title))}")


# ── test functions ────────────────────────────────────────────────────────


def test_health(base_url: str) -> None:
    _section("1. Health Check")
    try:
        t0 = time.perf_counter()
        resp = _get(f"{base_url}/api/health", timeout=10.0)
        latency = round((time.perf_counter() - t0) * 1000, 1)
        _check("HTTP 200", resp.status_code == 200, f"got {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            _check("status == ok", body.get("status") == "ok", f"got {body.get('status')!r}")
            _check("database == connected", body.get("database") == "connected", f"got {body.get('database')!r}")
            _check("db_latency_ms present", "db_latency_ms" in body, f"{body.get('db_latency_ms')} ms")
            _check("pool metrics present", "pool" in body and body["pool"].get("max", 0) > 0, str(body.get("pool", {})))
        _check("response latency < 2 000 ms", latency < 2000, f"{latency} ms")
    except Exception as exc:
        _check("health endpoint reachable", False, str(exc))


def test_auth(base_url: str, username: str, password: str) -> str | None:
    """Returns access token on success, None on failure."""
    _section("2. Authentication (JWT)")
    token: str | None = None
    try:
        resp = _post(
            f"{base_url}/api/auth/token",
            data={"username": username, "password": password},
            timeout=10.0,
        )
        _check("POST /api/auth/token HTTP 200", resp.status_code == 200, f"got {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            _check("access_token present", "access_token" in body)
            _check(
                "token_type == bearer",
                body.get("token_type", "").lower() == "bearer",
                f"got {body.get('token_type')!r}",
            )
            token = body.get("access_token")
    except Exception as exc:
        _check("auth endpoint reachable", False, str(exc))

    # Negative test: wrong credentials → 401
    try:
        resp_bad = _post(
            f"{base_url}/api/auth/token",
            data={"username": "invalid_user_xyz", "password": "wrong_pass_123"},
            timeout=10.0,
        )
        _check("Invalid credentials → 401", resp_bad.status_code == 401, f"got {resp_bad.status_code}")
    except Exception as exc:
        _check("auth negative test reachable", False, str(exc))

    return token


def test_protected_endpoints(base_url: str, token: str | None) -> None:
    _section("3. Protected Endpoints (requires valid token)")
    if token is None:
        _check("skip — no token available", False, "auth test failed, cannot proceed")
        return

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = _get(f"{base_url}/api/students/", headers=headers, timeout=10.0)
        _check("GET /api/students/ HTTP 200", resp.status_code == 200, f"got {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            _check("response contains 'data' list", isinstance(body.get("data"), list))
            _check("pagination keys present", "total" in body and "page" in body)
    except Exception as exc:
        _check("students endpoint reachable", False, str(exc))

    # No token → 401
    try:
        resp_no_auth = _get(f"{base_url}/api/students/", timeout=10.0)
        _check("No token → 401/403", resp_no_auth.status_code in (401, 403), f"got {resp_no_auth.status_code}")
    except Exception as exc:
        _check("unauthenticated request check", False, str(exc))


def test_api_docs(base_url: str) -> None:
    _section("4. OpenAPI docs accessible")
    try:
        resp = _get(f"{base_url}/api/docs", timeout=10.0)
        _check("GET /api/docs HTTP 200", resp.status_code == 200, f"got {resp.status_code}")
    except Exception as exc:
        _check("/api/docs reachable", False, str(exc))


# ── summary ──────────────────────────────────────────────────────────────


def _summary() -> int:
    passed = sum(1 for r in _results if r["passed"])
    failed = sum(1 for r in _results if not r["passed"])
    total = len(_results)
    print(f"\n{'═' * 65}")
    print(f"  SMOKE TEST SUMMARY — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─' * 65}")
    print(f"  Passed : {passed}/{total}")
    print(f"  Failed : {failed}/{total}")
    print(f"{'═' * 65}")
    if failed > 0:
        print("\n  Failing tests:")
        for r in _results:
            if not r["passed"]:
                print(f"    ❌ {r['name']}  — {r['detail']}")
        print()
    return 0 if failed == 0 else 1


# ── entry point ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="El Malick Gest — Smoke Tests")
    parser.add_argument(
        "--url",
        default=os.environ.get("ELMALICK_BASE_URL", "http://localhost:8000"),
        help="Base URL of the API server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("SMOKE_ADMIN_USER", "admin"),
        help="Admin username for auth test",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SMOKE_ADMIN_PASSWORD", "admin"),
        help="Admin password for auth test",
    )
    args = parser.parse_args()

    print(f"\n{'═' * 65}")
    print("  El Malick Gest — Smoke Tests")
    print(f"  Target: {args.url}")
    print(f"  Date  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═' * 65}")

    test_health(args.url)
    token = test_auth(args.url, args.user, args.password)
    test_protected_endpoints(args.url, token)
    test_api_docs(args.url)

    return _summary()


if __name__ == "__main__":
    sys.exit(main())
