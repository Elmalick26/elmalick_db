"""Phase 4 — Integration tests for previously-uncovered repositories.

Covers:
  • AcademicRepository    (src/data/academic_repo.py)
  • DisciplineRepository  (src/data/discipline_repo.py)
  • CommunicationRepository (src/data/communication_repo.py)
  • AdminDocumentsRepository (src/data/admin_documents_repo.py)

All tests use MagicMock connections — no live DB required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from repositories.academic_repo import AcademicRepository
from repositories.admin_documents_repo import AdminDocumentsRepository
from repositories.communication_repo import CommunicationRepository
from repositories.discipline_repo import DisciplineRepository

# ─── helpers ────────────────────────────────────────────────────────────────


def _conn():
    """Plain cursor mock (conn.cursor() → cur)."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def _multi_cursor(*return_values):
    """Connection that returns a fresh cursor on each call, cycling through
    the provided (fetchone, fetchall) pairs."""
    conn = MagicMock()
    cursors = []
    for fone, fall in return_values:
        c = MagicMock()
        c.fetchone.return_value = fone
        c.fetchall.return_value = fall if fall is not None else []
        cursors.append(c)
    conn.cursor.side_effect = cursors
    return conn


# ════════════════════════════════════════════════════════════════════════════
#  AcademicRepository
# ════════════════════════════════════════════════════════════════════════════


class TestAcademicRepository:
    # ── SchoolInfo ──────────────────────────────────────────────────────────

    def test_get_school_info_returns_row(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "Sénégal", "IA Dakar")
        repo = AcademicRepository(conn)
        row = repo.get_school_info()
        assert row == (1, "Sénégal", "IA Dakar")
        assert "SchoolInfo" in cur.execute.call_args[0][0]

    def test_get_school_info_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AcademicRepository(conn)
        assert repo.get_school_info() is None

    def test_save_school_info_deletes_then_inserts(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.save_school_info("Rép", "IA", "IEF", "École", "123", "Dakar", "33000000", "/logo.png", "M. Directeur")
        calls_sql = [str(c[0][0]) for c in cur.execute.call_args_list]
        assert any("DELETE FROM SchoolInfo" in s for s in calls_sql)
        assert any("INSERT INTO SchoolInfo" in s for s in calls_sql)

    # ── AcademicYears ───────────────────────────────────────────────────────

    def test_list_years(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "2024-2025", 1, "2024-09-01", "2025-07-31")]
        repo = AcademicRepository(conn)
        rows = repo.list_years()
        assert rows == [(1, "2024-2025", 1, "2024-09-01", "2025-07-31")]

    def test_get_year_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("2024-2025", "2024-09-01", "2025-07-31")
        repo = AcademicRepository(conn)
        assert repo.get_year(1) == ("2024-2025", "2024-09-01", "2025-07-31")

    def test_get_year_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AcademicRepository(conn)
        assert repo.get_year(999) is None

    def test_get_year_is_active_true(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1,)
        repo = AcademicRepository(conn)
        assert repo.get_year_is_active(1) is True

    def test_get_year_is_active_false(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (0,)
        repo = AcademicRepository(conn)
        assert repo.get_year_is_active(1) is False

    def test_get_year_is_active_none_row(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AcademicRepository(conn)
        assert repo.get_year_is_active(99) is False

    def test_upsert_year_update(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_year(5, "2025-2026")
        sql = cur.execute.call_args[0][0]
        assert "UPDATE AcademicYears" in sql

    def test_upsert_year_insert(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_year(None, "2025-2026")
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO AcademicYears" in sql

    def test_activate_year(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.activate_year(2)
        sqls = [c[0][0] for c in cur.execute.call_args_list]
        # first call deactivates all, second activates the one
        assert any("SET is_active=0" in s for s in sqls)
        assert any("SET is_active=1" in s for s in sqls)

    def test_delete_year(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.delete_year(3)
        sql = cur.execute.call_args[0][0]
        assert "DELETE FROM AcademicYears" in sql
        assert cur.execute.call_args[0][1] == (3,)

    # ── Cycles ──────────────────────────────────────────────────────────────

    def test_list_cycles(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Élémentaire", "ابتدائي")]
        repo = AcademicRepository(conn)
        assert repo.list_cycles() == [(1, "Élémentaire", "ابتدائي")]

    def test_get_cycle_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("Élémentaire", "ابتدائي")
        repo = AcademicRepository(conn)
        assert repo.get_cycle(1) == ("Élémentaire", "ابتدائي")

    def test_upsert_cycle_update(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_cycle(1, "Moyen", "متوسط")
        sql = cur.execute.call_args[0][0]
        assert "UPDATE Cycles" in sql

    def test_upsert_cycle_insert(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_cycle(None, "Nouveau", "جديد")
        sql = cur.execute.call_args[0][0]
        assert "INSERT INTO Cycles" in sql

    def test_delete_cycle(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.delete_cycle(4)
        assert "DELETE FROM Cycles" in cur.execute.call_args[0][0]

    # ── Classes ──────────────────────────────────────────────────────────────

    def test_list_classes_with_cycle(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Élémentaire", "CI", "CI")]
        repo = AcademicRepository(conn)
        rows = repo.list_classes_with_cycle()
        assert len(rows) == 1

    def test_get_class_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "CI", "CI", 1)
        repo = AcademicRepository(conn)
        assert repo.get_class(1) == (1, "CI", "CI", 1)

    def test_upsert_class_update(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_class(2, 1, "CE1", "CE1_AR", 3)
        assert "UPDATE Classes" in cur.execute.call_args[0][0]

    def test_upsert_class_insert(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_class(None, 1, "CE1", "CE1_AR", 3)
        assert "INSERT INTO Classes" in cur.execute.call_args[0][0]

    def test_delete_class(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.delete_class(7)
        assert "DELETE FROM Classes" in cur.execute.call_args[0][0]

    # ── Subjects ─────────────────────────────────────────────────────────────

    def test_list_subjects_with_cycle(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Élémentaire", "Mathématiques", "رياضيات", "FR", 2.0)]
        repo = AcademicRepository(conn)
        rows = repo.list_subjects_with_cycle()
        assert rows[0][2] == "Mathématiques"

    def test_get_subject(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "Mathématiques", "رياضيات", 2.0, "FR")
        repo = AcademicRepository(conn)
        assert repo.get_subject(1) is not None

    def test_upsert_subject_update(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_subject(1, 1, "Maths", "رياضيات", 2.0, "FR")
        assert "UPDATE Subjects" in cur.execute.call_args[0][0]

    def test_upsert_subject_insert(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.upsert_subject(None, 1, "Maths", "رياضيات", 2.0, "FR")
        assert "INSERT INTO Subjects" in cur.execute.call_args[0][0]

    def test_delete_subject(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.delete_subject(3)
        assert "DELETE FROM Subjects" in cur.execute.call_args[0][0]

    # ── Evaluations / Periods ─────────────────────────────────────────────────

    def test_list_evaluations(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Élémentaire", "T1", "Composition", "اختبار", "COMPO", 1.0)]
        repo = AcademicRepository(conn)
        rows = repo.list_evaluations()
        assert len(rows) == 1

    def test_delete_evaluation(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.delete_evaluation(5)
        assert "DELETE FROM AssessmentTypes" in cur.execute.call_args[0][0]

    def test_generate_periods_elementary(self):
        """For is_elementary=True, 3 periods × 1 COMPO each = 8 execute calls total."""
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (99,)  # RETURNING id
        conn.cursor.return_value = cur
        repo = AcademicRepository(conn)
        repo.generate_periods_and_assessments(
            1,
            1,
            is_elementary=True,
            year_start_date="2024-09-01",
            year_end_date="2025-07-31",
        )
        # Must have DELETE × 2, then INSERT AcademicPeriods × 3 + INSERT AssessmentTypes × 3
        assert cur.execute.call_count >= 8

    def test_generate_periods_secondary(self):
        """For is_elementary=False, 2 periods × 3 assessments each = 9 execute calls total."""
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = (99,)
        conn.cursor.return_value = cur
        repo = AcademicRepository(conn)
        repo.generate_periods_and_assessments(
            1,
            2,
            is_elementary=False,
            year_start_date="2024-09-01",
            year_end_date="2025-07-31",
        )
        assert cur.execute.call_count >= 9

    def test_list_periods_for_year_cycle(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Trimestre 1", "الفصل الأول", 1, "2024-09-01", "2024-12-01")]
        repo = AcademicRepository(conn)
        rows = repo.list_periods_for_year_cycle(1, 2)
        assert len(rows) == 1
        assert rows[0][0] == 1

    def test_update_period_dates(self):
        conn, cur = _conn()
        repo = AcademicRepository(conn)
        repo.update_period_dates(10, "2024-09-01", "2024-12-01")
        assert "UPDATE AcademicPeriods" in cur.execute.call_args[0][0]
        assert cur.execute.call_args[0][1] == ("2024-09-01", "2024-12-01", 10)


# ════════════════════════════════════════════════════════════════════════════
#  DisciplineRepository
# ════════════════════════════════════════════════════════════════════════════


class TestDisciplineRepository:
    # ── year / classes ───────────────────────────────────────────────────────

    def test_get_active_year_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (3,)
        repo = DisciplineRepository(conn)
        assert repo.get_active_year_id() == 3

    def test_get_active_year_fallback(self):
        """No active year → falls back to last year id."""
        conn = MagicMock()
        cur = MagicMock()
        # First call (is_active=1) → None, second call (ORDER BY id DESC) → (7,)
        cur.fetchone.side_effect = [None, (7,)]
        conn.cursor.return_value = cur
        repo = DisciplineRepository(conn)
        assert repo.get_active_year_id() == 7

    def test_get_active_year_none(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, None]
        conn.cursor.return_value = cur
        repo = DisciplineRepository(conn)
        assert repo.get_active_year_id() == -1

    def test_list_classes(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CI")]
        repo = DisciplineRepository(conn)
        rows = repo.list_classes()
        assert rows == [(1, "CI")]

    def test_get_cycle_name_for_class_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("Élémentaire",)
        repo = DisciplineRepository(conn)
        name = repo.get_cycle_name_for_class(1)
        assert name == "élémentaire"

    def test_get_cycle_name_for_class_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = DisciplineRepository(conn)
        assert repo.get_cycle_name_for_class(99) is None

    def test_get_cycle_id_for_class(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (2,)
        repo = DisciplineRepository(conn)
        assert repo.get_cycle_id_for_class(1) == 2

    def test_get_cycle_id_for_class_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = DisciplineRepository(conn)
        assert repo.get_cycle_id_for_class(99) is None

    def test_list_active_students_fullname(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Ahmed Diop")]
        repo = DisciplineRepository(conn)
        rows = repo.list_active_students_fullname(1, 1)
        assert rows == [(1, "Ahmed Diop")]

    # ── Periods ──────────────────────────────────────────────────────────────

    def test_list_periods_for_class_no_cycle(self):
        """Returns [] when no cycle_id found."""
        conn, cur = _conn()
        cur.fetchone.return_value = None  # get_cycle_id_for_class → None
        repo = DisciplineRepository(conn)
        result = repo.list_periods_for_class(99, 1)
        assert result == []

    def test_list_periods_for_class_with_cycle(self):
        conn = MagicMock()
        cur = MagicMock()
        # First call → get_cycle_id_for_class (returns 1)
        # Second call → list periods (returns rows)
        cur.fetchone.return_value = (1,)
        cur.fetchall.return_value = [(10, "Trimestre 1")]
        conn.cursor.return_value = cur
        repo = DisciplineRepository(conn)
        rows = repo.list_periods_for_class(1, 1)
        assert rows == [(10, "Trimestre 1")]

    def test_resolve_period_no_cycle(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = DisciplineRepository(conn)
        result = repo.resolve_period_id_for_class_date(1, "2025-01-15", 1)
        assert result is None

    def test_resolve_period_found(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [(2,), (5,)]  # cycle_id=2, then period_id=5
        conn.cursor.return_value = cur
        repo = DisciplineRepository(conn)
        result = repo.resolve_period_id_for_class_date(1, "2025-01-15", 1)
        assert result == 5

    # ── CRUD incidents ────────────────────────────────────────────────────────

    def test_insert_incident(self):
        conn, cur = _conn()
        repo = DisciplineRepository(conn)
        repo.insert_incident(1, "2025-01-01", "Absence", "Avertissement", 5, "Obs", 1, 2)
        assert "INSERT INTO StudentDiscipline" in cur.execute.call_args[0][0]

    def test_update_incident(self):
        conn, cur = _conn()
        repo = DisciplineRepository(conn)
        repo.update_incident(3, "2025-01-02", "Retard", "Punition", 2, "Note")
        assert "UPDATE StudentDiscipline" in cur.execute.call_args[0][0]

    def test_delete_incident(self):
        conn, cur = _conn()
        repo = DisciplineRepository(conn)
        repo.delete_incident(7)
        assert "DELETE FROM StudentDiscipline" in cur.execute.call_args[0][0]

    def test_get_incident_details_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "Ahmed Diop", "CI", 1, "2025-01-01", "Absence", "Avert.", 5, "Obs")
        repo = DisciplineRepository(conn)
        detail = repo.get_incident_details(1)
        assert detail is not None
        assert detail["student_name"] == "Ahmed Diop"
        assert detail["points"] == 5

    def test_get_incident_details_not_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = DisciplineRepository(conn)
        assert repo.get_incident_details(999) is None

    def test_get_incident_details_no_class(self):
        """class_name should default to '-' when C.class_name_fr is None."""
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "Ahmed Diop", None, None, "2025-01-01", "Absence", "Avert.", 5, "Obs")
        repo = DisciplineRepository(conn)
        detail = repo.get_incident_details(1)
        assert detail["class_name"] == "-"

    # ── Recent incidents + history ────────────────────────────────────────────

    def test_get_recent_incidents_with_year(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Ahmed", "2025-01-01", "Absence", 5)]
        repo = DisciplineRepository(conn)
        rows = repo.get_recent_incidents(year_id=1, limit=5)
        sql = cur.execute.call_args[0][0]
        assert "year_id" in sql
        assert rows[0][0] == "Ahmed"

    def test_get_recent_incidents_no_year(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = DisciplineRepository(conn)
        repo.get_recent_incidents(year_id=-1, limit=5)
        sql = cur.execute.call_args[0][0]
        assert "year_id" not in sql

    def test_get_history_no_filters(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = DisciplineRepository(conn)
        rows = repo.get_history(year_id=-1)
        assert rows == []

    def test_get_history_all_filters(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Ahmed Diop", "CI", "2025-01-01", "Abs", "Avert.", 5, "")]
        repo = DisciplineRepository(conn)
        rows = repo.get_history(year_id=1, class_id=2, period_id=3, search="Ahmed")
        assert len(rows) == 1

    def test_get_history_year_and_class_only(self):
        conn, cur = _conn()
        cur.fetchall.return_value = []
        repo = DisciplineRepository(conn)
        repo.get_history(year_id=1, class_id=2)
        sql = cur.execute.call_args[0][0]
        assert "year_id" in sql
        assert "SCN.class_id" in sql

    def test_get_school_info(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "Sénégal", "IA Dakar")
        repo = DisciplineRepository(conn)
        assert repo.get_school_info() == (1, "Sénégal", "IA Dakar")


# ════════════════════════════════════════════════════════════════════════════
#  CommunicationRepository
# ════════════════════════════════════════════════════════════════════════════


class TestCommunicationRepository:
    def test_get_active_year_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (2,)
        repo = CommunicationRepository(conn)
        assert repo.get_active_year_id() == 2

    def test_get_active_year_fallback(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, (5,)]
        conn.cursor.return_value = cur
        repo = CommunicationRepository(conn)
        assert repo.get_active_year_id() == 5

    def test_get_active_year_no_rows(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, None]
        conn.cursor.return_value = cur
        repo = CommunicationRepository(conn)
        assert repo.get_active_year_id() == -1

    def test_list_classes(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CI")]
        repo = CommunicationRepository(conn)
        assert repo.list_classes() == [(1, "CI")]

    def test_get_email_settings(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("smtp.gmail.com", "587", "test@test.com", "password")
        repo = CommunicationRepository(conn)
        result = repo.get_email_settings()
        assert result[0] == "smtp.gmail.com"

    def test_upsert_email_settings(self):
        conn, cur = _conn()
        repo = CommunicationRepository(conn)
        repo.upsert_email_settings("smtp.gmail.com", "587", "test@test.com", "pass")
        calls = [c[0][0] for c in cur.execute.call_args_list]
        assert any("DELETE FROM EmailSettings" in s for s in calls)
        assert any("INSERT INTO EmailSettings" in s for s in calls)

    def test_get_recipients_parents_of_class(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "Parent A", "parent@mail.com")]
        repo = CommunicationRepository(conn)
        rows = repo.get_recipients_parents_of_class(class_id=1, year_id=1)
        assert rows[0][1] == "Parent A"

    def test_get_recipients_all_staff(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "M. Ndiaye", "ndiaye@mail.com")]
        repo = CommunicationRepository(conn)
        assert repo.get_recipients_all_staff() == [(1, "M. Ndiaye", "ndiaye@mail.com")]

    def test_get_recipients_teachers(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(2, "Mme. Fall", "fall@mail.com")]
        repo = CommunicationRepository(conn)
        rows = repo.get_recipients_teachers()
        assert len(rows) == 1

    def test_insert_notification_log(self):
        conn, cur = _conn()
        repo = CommunicationRepository(conn)
        repo.insert_notification_log("tel:33000000", "Résultats", "sent", "", "2025-01-01 10:00:00")
        assert "INSERT INTO NotificationLogs" in cur.execute.call_args[0][0]

    def test_list_notification_logs(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("2025-01-01", "tel:33000000", "Résultats", "sent")]
        repo = CommunicationRepository(conn)
        rows = repo.list_notification_logs(limit=10)
        assert len(rows) == 1

    def test_get_notification_log_summary(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("2025-01-01", 5, 3)]
        repo = CommunicationRepository(conn)
        rows = repo.get_notification_log_summary("2025-01-01", "2025-01-31 23:59:59")
        assert len(rows) == 1


# ════════════════════════════════════════════════════════════════════════════
#  AdminDocumentsRepository
# ════════════════════════════════════════════════════════════════════════════


class TestAdminDocumentsRepository:
    def test_get_active_year_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1,)
        repo = AdminDocumentsRepository(conn)
        assert repo.get_active_year_id() == 1

    def test_get_active_year_fallback(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, (3,)]
        conn.cursor.return_value = cur
        repo = AdminDocumentsRepository(conn)
        assert repo.get_active_year_id() == 3

    def test_get_active_year_none(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.side_effect = [None, None]
        conn.cursor.return_value = cur
        repo = AdminDocumentsRepository(conn)
        assert repo.get_active_year_id() == -1

    def test_get_active_year_label_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("2024-2025",)
        repo = AdminDocumentsRepository(conn)
        assert repo.get_active_year_label() == "2024-2025"

    def test_get_active_year_label_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AdminDocumentsRepository(conn)
        assert repo.get_active_year_label() is None

    def test_list_classes(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(1, "CI"), (2, "CP")]
        repo = AdminDocumentsRepository(conn)
        assert len(repo.list_classes()) == 2

    def test_list_active_students_in_class(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(10, "Ahmed Diop"), (11, "Fatou Ba")]
        repo = AdminDocumentsRepository(conn)
        rows = repo.list_active_students_in_class(class_id=1, year_id=1)
        assert len(rows) == 2

    def test_list_student_ids_in_class(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [(10,), (11,), (12,)]
        repo = AdminDocumentsRepository(conn)
        ids = repo.list_student_ids_in_class(class_id=1, year_id=1)
        assert ids == [10, 11, 12]

    def test_get_student_photo_path_found(self):
        conn, cur = _conn()
        cur.fetchone.return_value = ("/photos/10.jpg",)
        repo = AdminDocumentsRepository(conn)
        assert repo.get_student_photo_path(10) == "/photos/10.jpg"

    def test_get_student_photo_path_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AdminDocumentsRepository(conn)
        assert repo.get_student_photo_path(99) is None

    def test_update_student_photo_path(self):
        conn, cur = _conn()
        repo = AdminDocumentsRepository(conn)
        repo.update_student_photo_path(10, "/new/photo.jpg")
        assert "UPDATE Students" in cur.execute.call_args[0][0]
        assert cur.execute.call_args[0][1] == ("/new/photo.jpg", 10)

    def test_get_student_full_data(self):
        conn, cur = _conn()
        row = (
            10,
            "Ahmed Diop",
            "2010-01-01",
            "Dakar",
            "CI",
            "Parent A",
            "/photo.jpg",
            "Dakar",
            "33000000",
            "2024-10-01",
            "05",
            "EMG-0001",
        )
        cur.fetchone.return_value = row
        repo = AdminDocumentsRepository(conn)
        result = repo.get_student_full_data(student_id=10, year_id=1)
        assert result == row

    def test_get_student_full_data_none(self):
        conn, cur = _conn()
        cur.fetchone.return_value = None
        repo = AdminDocumentsRepository(conn)
        assert repo.get_student_full_data(99, 1) is None

    def test_get_student_dues(self):
        conn, cur = _conn()
        cur.fetchall.return_value = [("Inscription", "Frais d'inscription", 50000, "2024-10-01", 0)]
        repo = AdminDocumentsRepository(conn)
        rows = repo.get_student_dues(student_id=10, year_id=1)
        assert len(rows) == 1

    def test_get_school_info(self):
        conn, cur = _conn()
        cur.fetchone.return_value = (1, "Sénégal", "IA Dakar")
        repo = AdminDocumentsRepository(conn)
        assert repo.get_school_info() == (1, "Sénégal", "IA Dakar")
