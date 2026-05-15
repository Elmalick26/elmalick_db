"""
tests/test_api_endpoints.py
اختبارات شاملة لـ REST API باستخدام FastAPI TestClient.
يغطي: auth, students, parent portal
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta

from fastapi.testclient import TestClient

from api.main import app
from api.auth import create_access_token, SECRET_KEY, ALGORITHM

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_admin_token() -> str:
    """Token JWT valide pour admin."""
    return create_access_token({"sub": "admin", "role": "Admin"})


def _make_parent_token(student_id: int = 1) -> str:
    """Token JWT valide pour parent."""
    return create_access_token(
        {"student_id": student_id, "role": "parent"},
        expires_delta=timedelta(minutes=120),
    )


def _make_db_mock(conn_mock=None):
    """Return a mock DatabaseManager that yields conn_mock."""
    db = MagicMock()
    conn = conn_mock or MagicMock()
    db.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
    db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    return db, conn


# ─────────────────────────────────────────────────────────────
# 1. General API
# ─────────────────────────────────────────────────────────────

class TestApiHealth:
    def test_root_redirects_or_404(self):
        r = client.get("/")
        assert r.status_code in (200, 404, 307)

    def test_docs_available(self):
        r = client.get("/api/docs")
        assert r.status_code == 200

    def test_openapi_json(self):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "openapi" in data
        assert data["info"]["title"] == "El Malick Gest API"


# ─────────────────────────────────────────────────────────────
# 2. Auth — POST /api/auth/token
# ─────────────────────────────────────────────────────────────

class TestAuthToken:
    def test_login_wrong_credentials_returns_401(self):
        with patch("api.auth._verify_user", return_value=None):
            r = client.post(
                "/api/auth/token",
                data={"username": "bad", "password": "bad"},
            )
        assert r.status_code == 401
        assert "Identifiants" in r.json()["detail"]

    def test_login_success_returns_token(self):
        user = {"id": 1, "username": "admin", "role": "Admin"}
        with patch("api.auth._verify_user", return_value=user):
            r = client.post(
                "/api/auth/token",
                data={"username": "admin", "password": "admin"},
            )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["role"] == "Admin"
        assert body["username"] == "admin"

    def test_login_missing_fields_returns_422(self):
        r = client.post("/api/auth/token", data={})
        assert r.status_code == 422

    def test_protected_route_without_token_returns_401(self):
        r = client.get("/api/students/")
        assert r.status_code == 401

    def test_protected_route_with_invalid_token_returns_401(self):
        r = client.get(
            "/api/students/",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────
# 3. Students routes — GET /api/students/
# ─────────────────────────────────────────────────────────────

class TestStudentsRoutes:
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {_make_admin_token()}"}

    def test_list_students_success(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.list_students.return_value = [
            {"id": 1, "first_name_fr": "Ahmed", "last_name_fr": "Ba", "class_name_fr": "CM2"}
        ]
        repo_mock.count_students.return_value = 1

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/", headers=self._auth_headers())

        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert len(body["data"]) == 1

    def test_list_students_with_search(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.list_students.return_value = []
        repo_mock.count_students.return_value = 0

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/?q=Ahmed&page=1&page_size=10", headers=self._auth_headers())

        assert r.status_code == 200
        repo_mock.list_students.assert_called_once_with(1, "Ahmed", 10, 0)

    def test_list_students_db_error_returns_500(self):
        db = MagicMock()
        db.get_connection.side_effect = Exception("DB down")

        with patch("api.routes_students.DatabaseManager", return_value=db):
            r = client.get("/api/students/", headers=self._auth_headers())

        assert r.status_code == 500

    def test_get_student_found(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_student_by_id.return_value = {"id": 5, "first_name_fr": "Ali"}

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/5", headers=self._auth_headers())

        assert r.status_code == 200
        assert r.json()["id"] == 5

    def test_get_student_not_found_returns_404(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_student_by_id.return_value = None

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/999", headers=self._auth_headers())

        assert r.status_code == 404

    def test_get_student_grades(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_grades.return_value = [{"subject": "Maths", "score": 15.0}]

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/1/grades", headers=self._auth_headers())

        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_student_attendance(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_attendance.return_value = [{"date": "2026-01-10", "status": "Présent"}]

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/1/attendance", headers=self._auth_headers())

        assert r.status_code == 200

    def test_get_student_dues(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_dues.return_value = [{"fee_type": "Inscription", "net_amount": 50000}]

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/1/dues", headers=self._auth_headers())

        assert r.status_code == 200

    def test_teacher_role_can_access_students(self):
        token = create_access_token({"sub": "teacher1", "role": "Teacher"})
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.list_students.return_value = []
        repo_mock.count_students.return_value = 0

        with patch("api.routes_students.DatabaseManager", return_value=db), patch(
            "api.routes_students.StudentsApiRepository", return_value=repo_mock
        ):
            r = client.get("/api/students/", headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 200

    def test_parent_role_cannot_access_students(self):
        """Parent role should not access /api/students/ — requires Admin/Teacher/Staff."""
        token = create_access_token({"sub": "parent1", "role": "Parent"})
        r = client.get("/api/students/", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────
# 4. Parent Portal — POST /api/parent/login
# ─────────────────────────────────────────────────────────────

class TestParentPortal:
    def test_parent_login_wrong_code_returns_404(self):
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_student_for_parent_login.return_value = None  # code introuvable

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.post(
                "/api/parent/login",
                json={"student_code": "EMG-9999", "pin": "1234"},
            )
        assert r.status_code == 404

    def test_parent_login_wrong_pin_returns_401(self):
        import bcrypt

        hashed = bcrypt.hashpw(b"5678", bcrypt.gensalt()).decode()
        # tuple: (s_id, fn, ln, p_name, p_phone, pin_hash, pin_plain, scode)
        row = (1, "Ahmed", "Ba", "Parent Name", "0700000000", hashed, None, "EMG-0001")
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_student_for_parent_login.return_value = row

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.post(
                "/api/parent/login",
                json={"student_code": "EMG-0001", "pin": "1234"},  # wrong PIN
            )
        assert r.status_code == 401

    def test_parent_login_success_with_hash(self):
        import bcrypt

        pin = "1234"
        hashed = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
        row = (1, "Ahmed", "Ba", "Parent Name", "0700000000", hashed, None, "EMG-0001")
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_student_for_parent_login.return_value = row

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.post(
                "/api/parent/login",
                json={"student_code": "EMG-0001", "pin": pin},
            )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["student_code"] == "EMG-0001"

    def test_parent_login_first_access_no_pin(self):
        """First access: no pin stored → accept any PIN ≥ 4 digits and register it."""
        row = (1, "Ahmed", "Ba", "Parent Name", "0700000000", None, None, "EMG-0001")
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_student_for_parent_login.return_value = row

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.post(
                "/api/parent/login",
                json={"student_code": "EMG-0001", "pin": "9999"},
            )
        assert r.status_code == 200

    def test_parent_me_without_token_returns_401(self):
        r = client.get("/api/parent/me")
        assert r.status_code == 401

    def test_parent_me_with_valid_token(self):
        token = _make_parent_token(student_id=1)
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_student_info.return_value = {"id": 1, "first_name_fr": "Ahmed"}

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.get("/api/parent/me", headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 200

    def test_parent_me_student_not_found_returns_404(self):
        token = _make_parent_token(student_id=999)
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_student_info.return_value = None

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.get("/api/parent/me", headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 404

    def test_parent_grades(self):
        token = _make_parent_token(student_id=1)
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_student_grades.return_value = [{"subject_name_fr": "Maths", "score": 18.0}]

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.get("/api/parent/grades", headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 200

    def test_parent_attendance(self):
        token = _make_parent_token(student_id=1)
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_student_attendance.return_value = []

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.get("/api/parent/attendance", headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 200

    def test_parent_dues(self):
        token = _make_parent_token(student_id=1)
        db, conn = _make_db_mock()
        repo_mock = MagicMock()
        repo_mock.get_active_year_id.return_value = 1
        repo_mock.get_student_dues.return_value = [{"fee_type": "Mensualité", "net_amount": 20000}]

        with patch("api.routes_parent.DatabaseManager", return_value=db), patch(
            "api.routes_parent.ParentRepository", return_value=repo_mock
        ):
            r = client.get("/api/parent/dues", headers={"Authorization": f"Bearer {token}"})

        assert r.status_code == 200
    def test_admin_token_cannot_use_parent_me(self):
        """Admin token doesn't have student_id → should fail parent endpoint."""
        admin_token = _make_admin_token()
        r = client.get("/api/parent/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────
# 5. JWT helpers
# ─────────────────────────────────────────────────────────────

class TestJWTHelpers:
    def test_create_access_token_contains_sub(self):
        from jose import jwt as jose_jwt

        token = create_access_token({"sub": "testuser", "role": "Admin"})
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["role"] == "Admin"

    def test_create_access_token_with_expiry(self):
        from jose import jwt as jose_jwt

        token = create_access_token({"sub": "u", "role": "Admin"}, expires_delta=timedelta(minutes=5))
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
