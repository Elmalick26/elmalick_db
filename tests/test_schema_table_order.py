"""H1 — db_schema must create Timetable before tables that FK to it.

StudentAttendance and StudentDiscipline carry a FOREIGN KEY to Timetable. If
Timetable is created after them, a clean-database initialise_schema() fails with
"relation timetable does not exist". This source-order guard prevents the
regression without needing a live database.
"""

from __future__ import annotations

import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db_schema


def _pos(src, table):
    return src.index(f"CREATE TABLE IF NOT EXISTS {table}")


def test_timetable_created_before_dependents():
    src = inspect.getsource(db_schema)
    timetable = _pos(src, "Timetable")
    attendance = _pos(src, "StudentAttendance")
    discipline = _pos(src, "StudentDiscipline")
    assert timetable < attendance, "Timetable must be created before StudentAttendance"
    assert timetable < discipline, "Timetable must be created before StudentDiscipline"
