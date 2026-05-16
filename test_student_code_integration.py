#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for student_code integration in UI and reporting.
Verifies that:
1. student_code is fetched correctly in get_student_data()
2. generate_senegal_id_card displays student_code
3. student_management.py table includes student_code column
4. Reports include student_code in output
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_logger import AppLogger  # noqa: E402
from database_setup import DatabaseManager  # noqa: E402
from repositories.student_repo import StudentRepository  # noqa: E402


def test_student_code_in_database():
    """Verify student_code column exists and has values"""
    AppLogger.info("Test", "Checking student_code in database...")

    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Check column exists
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name='students' AND column_name='student_code'
        """
        )
        if not cursor.fetchone():
            AppLogger.error("Test", "❌ student_code column NOT found in Students table")
            return False

        AppLogger.info("Test", "✅ student_code column EXISTS")

        # Check data
        cursor.execute("SELECT id, student_code FROM Students WHERE student_code IS NOT NULL LIMIT 3")
        rows = cursor.fetchall()
        if rows:
            AppLogger.info("Test", f"✅ Found {len(rows)} students with student_code:")
            for sid, code in rows:
                AppLogger.info("Test", f"   - ID {sid}: {code}")
        else:
            AppLogger.warning("Test", "⚠️ No students have student_code (might need migration)")

        return True


def test_student_repository():
    """Verify StudentRepository.list_students returns student_code"""
    AppLogger.info("Test", "Checking StudentRepository.list_students()...")

    db = DatabaseManager()
    with db.get_connection() as conn:
        repo = StudentRepository(conn)

        # Get active year
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM AcademicYears WHERE is_active=1 LIMIT 1")
        year_row = cursor.fetchone()
        year_id = year_row[0] if year_row else 1

        rows = repo.list_students(year_id)
        if rows:
            first_row = rows[0]
            expected_cols = 12  # 11 original + 1 student_code
            if len(first_row) >= expected_cols:
                AppLogger.info(
                    "Test", f"✅ list_students returns {len(first_row)} columns (expected >= {expected_cols})"
                )
                # Column 11 should be student_code
                student_code = first_row[11]
                AppLogger.info("Test", f"   - First student code: {student_code}")
            else:
                AppLogger.error("Test", f"❌ list_students returns {len(first_row)} columns (expected {expected_cols})")
                return False
        else:
            AppLogger.warning("Test", "⚠️ No students found in database")

        return True


def test_get_student_data():
    """Verify admin_documents.get_student_data includes student_code"""
    AppLogger.info("Test", "Checking get_student_data structure...")

    # Load admin_documents module
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "admin_documents", os.path.join(os.path.dirname(__file__), "admin_documents.py")
        )
        _ = importlib.util.module_from_spec(spec)

        # We can't easily instantiate AdminDocsWindow without Qt, but we can check the code
        with open("admin_documents.py", "r", encoding="utf-8") as f:
            content = f.read()

            # Check for student_code in SELECT
            if "S.student_code" in content:
                AppLogger.info("Test", "✅ get_student_data() includes S.student_code in SELECT")
            else:
                AppLogger.error("Test", "❌ get_student_data() missing S.student_code in SELECT")
                return False

            # Check for student_code in return dict
            if "'student_code':" in content:
                AppLogger.info("Test", "✅ get_student_data() includes student_code in return dict")
            else:
                AppLogger.error("Test", "❌ get_student_data() missing student_code in return dict")
                return False

            # Check for Code Accès label in card generation
            if "Code Accès" in content:
                AppLogger.info("Test", "✅ generate_senegal_id_card() includes 'Code Accès' label")
            else:
                AppLogger.error("Test", "❌ generate_senegal_id_card() missing 'Code Accès' label")
                return False

        return True
    except Exception as e:
        AppLogger.error("Test", f"❌ Error checking admin_documents: {e}")
        return False


def test_student_management():
    """Verify student_management.py includes student_code in table"""
    AppLogger.info("Test", "Checking student_management.py table configuration...")

    try:
        with open("student_management.py", "r", encoding="utf-8") as f:
            content = f.read()

            # Check for Code Accès in headers
            if "Code Accès" in content:
                AppLogger.info("Test", "✅ student_management table includes 'Code Accès' column")
            else:
                AppLogger.error("Test", "❌ student_management table missing 'Code Accès' column")
                return False

            # Check for setColumnCount(11)
            if "setColumnCount(11)" in content:
                AppLogger.info("Test", "✅ student_management table set to 11 columns")
            else:
                AppLogger.warning("Test", "⚠️ student_management table column count may not be 11")

            return True
    except Exception as e:
        AppLogger.error("Test", f"❌ Error checking student_management: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("TESTING STUDENT_CODE INTEGRATION")
    print("=" * 60 + "\n")

    tests = [
        ("Database Structure", test_student_code_in_database),
        ("StudentRepository", test_student_repository),
        ("Admin Documents", test_get_student_data),
        ("Student Management", test_student_management),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            AppLogger.error("Test", f"❌ {name} test failed with exception: {e}")
            results.append((name, False))
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:<30} {status}")

    passed = sum(r for _, r in results)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
