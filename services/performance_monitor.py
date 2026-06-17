"""services/performance_monitor.py — Query Performance Baseline Tooling (T9.1 / T9.2)

Usage (one-time baseline capture):
    python -m services.performance_monitor

Public API:
    enable_pg_stat_statements(conn)   — CREATE EXTENSION IF NOT EXISTS pg_stat_statements
    get_top_slow_queries(conn, n=10)  — SELECT FROM pg_stat_statements ORDER BY total_exec_time
    explain_query(conn, sql, params)  — EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
    save_baseline_report(conn, path)  — full JSON report saved to school_data/

T9.2 static analysis is embedded in SLOW_QUERY_CANDIDATES below.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger("PerformanceMonitor")

# ── T9.2 : Static Analysis — candidates identified by code review ────────────
# Ordered by Impact × Effort score (descending).
SLOW_QUERY_CANDIDATES: list[dict] = [
    {
        "id": "C1",
        "description": "list_students — 4-column ILIKE search on Students",
        "issue_type": "Missing GIN index (text search without pg_trgm)",
        "impact": "HIGH",
        "effort": "LOW",
        "recommendation": "Enable pg_trgm + 4 GIN indexes — revision 007",
        "status": "FIXED_IN_007",
        "location": "src/data/students_api_repo.py :: list_students()",
    },
    {
        "id": "C2",
        "description": "list_late_payers — N+1 correlated subqueries in SELECT + HAVING",
        "issue_type": "N+1: 4 correlated subqueries per row in SELECT; 2 in HAVING",
        "impact": "HIGH",
        "effort": "MEDIUM",
        "recommendation": "Rewrite with single CTE + LEFT JOIN aggregate (T10.2)",
        "status": "FIXED_IN_T10_2",
        "location": "src/data/finance_repo.py :: list_late_payers()",
        "fix": "Replaced 6 correlated subqueries with CTE paid AS (SELECT COALESCE(due_id,month_index), SUM(amount_paid)) + LEFT JOIN",
    },
    {
        "id": "C3",
        "description": "StudentClassNumbers — no composite index (student_id, year_id)",
        "issue_type": "Missing composite index — table used in every student list/grade/attendance join",
        "impact": "HIGH",
        "effort": "LOW",
        "recommendation": "CREATE INDEX ... ON StudentClassNumbers (student_id, year_id, class_id) — revision 007",
        "status": "FIXED_IN_007",
        "location": "all repos joining StudentClassNumbers",
    },
    {
        "id": "C4",
        "description": "Grades — no composite index (student_id, year_id)",
        "issue_type": "Missing composite index — used in grade sheets and reports",
        "impact": "MEDIUM",
        "effort": "LOW",
        "recommendation": "CREATE INDEX ... ON Grades (student_id, year_id) — revision 007",
        "status": "FIXED_IN_007",
        "location": "src/data/grades_repo.py and src/data/students_api_repo.py",
    },
    {
        "id": "C5",
        "description": "StudentAttendance — no composite index (student_id, year_id)",
        "issue_type": "Missing composite index — used in attendance reports",
        "impact": "MEDIUM",
        "effort": "LOW",
        "recommendation": "CREATE INDEX ... ON StudentAttendance (student_id, year_id) — revision 007",
        "status": "FIXED_IN_007",
        "location": "src/data/attendance_repo.py",
    },
    {
        "id": "C6",
        "description": "StudentDues — no composite index (student_id, year_id)",
        "issue_type": "Missing composite index — used in payment and dues lookups",
        "impact": "MEDIUM",
        "effort": "LOW",
        "recommendation": "CREATE INDEX ... ON StudentDues (student_id, year_id) — revision 007",
        "status": "FIXED_IN_007",
        "location": "src/data/finance_repo.py",
    },
]

# ── T9.1 : Target queries to EXPLAIN in a baseline run ──────────────────────
EXPLAIN_TARGETS: list[dict] = [
    {
        "id": "Q1",
        "label": "list_students — no search filter",
        "sql": """
            SELECT S.id, S.first_name_fr, S.last_name_fr,
                   S.first_name_ar, S.last_name_ar,
                   S.gender, S.birth_date, S.status,
                   C.class_name_fr AS class_name
            FROM Students S
            LEFT JOIN StudentClassNumbers SCN
                   ON S.id = SCN.student_id AND SCN.year_id = (
                       SELECT id FROM AcademicYears WHERE is_active = 1 ORDER BY id DESC LIMIT 1
                   )
            LEFT JOIN Classes C ON SCN.class_id = C.id
            WHERE S.status != 'Archived'
            ORDER BY S.last_name_fr, S.first_name_fr
            LIMIT 20 OFFSET 0
        """,
        "params": [],
    },
    {
        "id": "Q2",
        "label": "list_students — ILIKE text search",
        "sql": """
            SELECT S.id, S.first_name_fr, S.last_name_fr
            FROM Students S
            WHERE S.status != 'Archived'
              AND (S.first_name_fr ILIKE %s OR S.last_name_fr ILIKE %s
                   OR S.first_name_ar ILIKE %s OR S.last_name_ar ILIKE %s)
            LIMIT 20 OFFSET 0
        """,
        "params": ["%ali%", "%ali%", "%علي%", "%علي%"],
    },
    {
        "id": "Q3",
        "label": "list_dues_for_student",
        "sql": """
            SELECT D.id, D.fee_description, D.net_amount, D.is_paid, D.due_date
            FROM StudentDues D
            WHERE D.student_id = (SELECT id FROM Students LIMIT 1)
              AND D.year_id = (SELECT id FROM AcademicYears WHERE is_active = 1 LIMIT 1)
            ORDER BY D.due_date ASC
        """,
        "params": [],
    },
    {
        "id": "Q4",
        "label": "get_grades — student + year join",
        "sql": """
            SELECT G.score, SB.subject_name_fr, SB.coefficient,
                   AP.period_name_fr, AT.name_fr
            FROM Grades G
            JOIN Subjects SB ON G.subject_id = SB.id
            JOIN AssessmentTypes AT ON G.assessment_id = AT.id
            JOIN AcademicPeriods AP ON AT.period_id = AP.id
            JOIN StudentClassNumbers SCN
                 ON G.student_id = SCN.student_id AND SCN.year_id = G.year_id
            JOIN Classes CL ON SCN.class_id = CL.id
            JOIN Cycles CY ON CL.cycle_id = CY.id
            WHERE G.student_id = (SELECT id FROM Students LIMIT 1)
              AND G.year_id = (SELECT id FROM AcademicYears WHERE is_active = 1 LIMIT 1)
            ORDER BY AP.sort_order, SB.subject_name_fr
        """,
        "params": [],
    },
    {
        "id": "Q5",
        "label": "StudentAttendance per student/year",
        "sql": """
            SELECT date, status, reason
            FROM StudentAttendance
            WHERE student_id = (SELECT id FROM Students LIMIT 1)
              AND year_id = (SELECT id FROM AcademicYears WHERE is_active = 1 LIMIT 1)
            ORDER BY date DESC LIMIT 90
        """,
        "params": [],
    },
]


# ── Public API ───────────────────────────────────────────────────────────────


def enable_pg_stat_statements(conn: Any) -> bool:
    """Enable pg_stat_statements extension. Returns True if successfully enabled."""
    try:
        cursor = conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
        conn.commit()
        logger.info("pg_stat_statements extension enabled.")
        return True
    except Exception as e:
        logger.warning(f"Could not enable pg_stat_statements: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def get_top_slow_queries(conn: Any, n: int = 10) -> list[dict]:
    """Return top-n slowest queries from pg_stat_statements.

    Requires pg_stat_statements to be enabled and caller to have
    pg_read_all_stats privilege (or be superuser).
    Returns empty list if extension is unavailable.
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT query,
                   calls,
                   ROUND(total_exec_time::numeric, 2)  AS total_ms,
                   ROUND(mean_exec_time::numeric, 2)   AS mean_ms,
                   ROUND(stddev_exec_time::numeric, 2) AS stddev_ms,
                   rows
            FROM pg_stat_statements
            WHERE query NOT ILIKE '%pg_stat_statements%'
            ORDER BY total_exec_time DESC
            LIMIT %s
            """,
            (n,),
        )
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"pg_stat_statements query failed (extension enabled?): {e}")
        return []


def explain_query(conn: Any, sql: str, params: list | None = None) -> dict:
    """Run EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) and return the plan as a dict.

    Uses ROLLBACK after execution to avoid side-effects from ANALYZE.
    """
    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
    try:
        cursor = conn.cursor()
        cursor.execute(explain_sql, params or [])
        result = cursor.fetchone()
        conn.rollback()  # ANALYZE actually executes the query — rollback immediately
        return result[0] if result else {}
    except Exception as e:
        logger.warning(f"EXPLAIN failed for query: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return {"error": str(e)}


# ── T10.4 Comparison report (static analysis) ────────────────────────────────
_COMPARISON_RESULTS: list[dict] = [
    {
        "candidate": "C1",
        "query": "list_students ILIKE text search",
        "before": {
            "plan_type": "Seq Scan",
            "issue": "4x ILIKE on unindexed text columns",
            "estimated_cost": "O(n) per column per search",
        },
        "after": {
            "plan_type": "Bitmap Heap Scan (GIN)",
            "fix": "pg_trgm extension + 4 GIN indexes (revision 007)",
            "estimated_cost": "O(log n)",
        },
        "improvement": "Seq Scan → GIN index scan; scales with large student datasets",
        "status": "FIXED_IN_007",
    },
    {
        "candidate": "C2",
        "query": "list_late_payers",
        "before": {
            "subqueries_per_row": 6,
            "pattern": "4 correlated subqueries in SELECT CASE + 2 in HAVING CASE",
            "estimated_cost": "O(n × m) — n dues rows × m payments per due",
        },
        "after": {
            "subqueries_per_row": 0,
            "pattern": "1 CTE (paid) pre-aggregated + 1 LEFT JOIN",
            "estimated_cost": "O(n + m) — linear over dues + payments",
        },
        "improvement": "Eliminated 6 correlated subqueries; MonthlyPaymentsStatus scanned once",
        "status": "FIXED_IN_T10_2",
    },
    {
        "candidate": "C3",
        "query": "All queries joining StudentClassNumbers(student_id, year_id)",
        "before": {"plan_type": "Seq Scan or partial index scan", "issue": "No composite index"},
        "after": {"plan_type": "Index Scan (idx_scn_student_year_class)", "fix": "revision 007"},
        "improvement": "Composite index avoids full table scan on every student list",
        "status": "FIXED_IN_007",
    },
    {
        "candidate": "C4",
        "query": "Grades per student/year",
        "before": {"plan_type": "Seq Scan", "issue": "No composite index on (student_id, year_id)"},
        "after": {"plan_type": "Index Scan (idx_grades_student_year)", "fix": "revision 007"},
        "improvement": "Index lookup replaces full scan in grade sheet and bulletin generation",
        "status": "FIXED_IN_007",
    },
    {
        "candidate": "C5",
        "query": "StudentAttendance per student/year",
        "before": {"plan_type": "Seq Scan", "issue": "No composite index"},
        "after": {"plan_type": "Index Scan (idx_attendance_student_year)", "fix": "revision 007"},
        "improvement": "Attendance report query uses index instead of full table scan",
        "status": "FIXED_IN_007",
    },
    {
        "candidate": "C6",
        "query": "StudentDues per student/year",
        "before": {"plan_type": "Seq Scan", "issue": "No composite index"},
        "after": {"plan_type": "Index Scan (idx_dues_student_year)", "fix": "revision 007"},
        "improvement": "Payment and dues lookups use index — affects list_late_payers, list_dues_for_student",
        "status": "FIXED_IN_007",
    },
]


def save_comparison_report(output_dir: str = "school_data") -> str:
    """Save a static before/after performance comparison report (T10.4).

    Does not require a database connection — based on code analysis of
    SLOW_QUERY_CANDIDATES vs. the fixes applied in T10.2 and revision 007.
    Saves to ``output_dir/perf_comparison_YYYY-MM-DD.json``.
    Returns the absolute path to the saved file.
    """
    today = date.today().strftime("%Y-%m-%d")
    out_path = Path(output_dir) / f"perf_comparison_{today}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "generated_at": today,
        "tool": "services/performance_monitor.py :: save_comparison_report",
        "summary": {
            "candidates_identified": len(SLOW_QUERY_CANDIDATES),
            "candidates_fixed": sum(1 for c in SLOW_QUERY_CANDIDATES if "FIXED" in c["status"]),
            "alembic_revision": "007",
            "n1_queries_fixed": 1,
            "new_indexes": 8,
        },
        "comparisons": _COMPARISON_RESULTS,
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Performance comparison report saved → {out_path}")
    return str(out_path)


def save_baseline_report(conn: Any, output_dir: str = "school_data") -> str:
    """Capture pg_stat_statements top-10 + EXPLAIN plans for all EXPLAIN_TARGETS.

    Saves a JSON file to ``output_dir/perf_baseline_YYYY-MM-DD.json``.
    Returns the absolute path to the saved file.
    """
    today = date.today().strftime("%Y-%m-%d")
    out_path = Path(output_dir) / f"perf_baseline_{today}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "generated_at": today,
        "tool": "services/performance_monitor.py",
        "slow_query_candidates": SLOW_QUERY_CANDIDATES,
        "pg_stat_statements_top10": get_top_slow_queries(conn, 10),
        "explain_plans": [],
    }

    for target in EXPLAIN_TARGETS:
        logger.info(f"EXPLAIN {target['id']}: {target['label']}")
        plan = explain_query(conn, target["sql"], target.get("params"))
        report["explain_plans"].append({"id": target["id"], "label": target["label"], "plan": plan})

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Performance baseline report saved → {out_path}")
    return str(out_path)


# ── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # Add project root to sys.path when run directly
    _root = Path(__file__).parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    os.chdir(_root)

    from database_setup import DatabaseManager  # noqa: E402

    db = DatabaseManager()
    with db.get_connection() as conn:
        print("Step 1 — enabling pg_stat_statements …")
        ok = enable_pg_stat_statements(conn)
        if not ok:
            print("  WARNING: pg_stat_statements could not be enabled (may need superuser).")

        print("Step 2 — saving baseline report …")
        path = save_baseline_report(conn)
        print(f"  Report saved: {path}")

    print("Done.")
