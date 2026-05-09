#!/usr/bin/env python3
"""Parent portal end-to-end test using permanent student_code."""

from fastapi.testclient import TestClient

from api.main import app
from database_setup import DatabaseManager


client = TestClient(app)


def _get_active_student_for_portal():
    db = DatabaseManager()
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT S.student_code, S.id, S.first_name_fr, S.last_name_fr,
                   S.parent_name, AY.year_label
            FROM StudentClassNumbers SCN
            JOIN Students S ON SCN.student_id = S.id
            JOIN AcademicYears AY ON SCN.year_id = AY.id
            WHERE AY.is_active = 1
              AND S.status != 'Archived'
              AND S.student_code IS NOT NULL
            ORDER BY S.id ASC
            LIMIT 1
            """
        )
        return cur.fetchone()


def test_parent_portal_login_end_to_end():
    row = _get_active_student_for_portal()
    assert row is not None, "No active student with student_code found"

    student_code, _student_id, _fname, _lname, _parent_name, _year = row
    test_pin = "9999"

    resp = client.post(
        "/api/parent/login",
        json={"student_code": str(student_code), "pin": test_pin},
    )
    assert resp.status_code == 200, resp.json()
    login_data = resp.json()
    assert "access_token" in login_data
    parent_token = login_data["access_token"]

    resp = client.post(
        "/api/parent/login",
        json={"student_code": str(student_code), "pin": test_pin},
    )
    assert resp.status_code == 200, resp.json()

    headers = {"Authorization": f"Bearer {parent_token}"}

    resp = client.get("/api/parent/me", headers=headers)
    assert resp.status_code == 200, resp.json()
    profile = resp.json()
    assert profile.get("first_name_fr") is not None
    assert profile.get("last_name_fr") is not None
    assert profile.get("class_name") is not None
    assert profile.get("academic_year") is not None
    assert profile.get("academic_year") == _year

    resp = client.get("/api/parent/grades", headers=headers)
    assert resp.status_code == 200, resp.json()

    resp = client.get("/api/parent/dues", headers=headers)
    assert resp.status_code == 200, resp.json()
