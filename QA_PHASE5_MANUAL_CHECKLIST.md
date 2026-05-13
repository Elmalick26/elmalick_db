# QA Manual Checklist — Phase 5.1-5.2 Closure

Date: 08 May 2026
Scope: Final manual validation for parent portal + student_code UI integration.

## 1) Pre-checks

- Confirm API server is running on `http://127.0.0.1:8000`.
- Confirm desktop app launches from `main_dashbord.py`.
- Confirm database has students with non-null `student_code` (EMG-XXXX).

## 2) Parent Portal Login Flow

URL: `http://127.0.0.1:8000/portal`

- Open portal login page.
- Verify label shows: `Code de l'eleve` (or equivalent code label).
- Verify placeholder shows EMG format example.
- Login with a valid pair (`student_code` + PIN).
- Expected:
  - Login succeeds.
  - Student info card appears.
  - No unknown error message.

Negative checks:

- Wrong code -> expected `404` style message (`code introuvable`).
- Wrong PIN for existing code -> expected `401` style message.

## 3) Student Management Table (Desktop)

Module: student management list screen.

- Open full students table.
- Verify column `Code Acces` is visible.
- Verify each listed student row shows a code value (`EMG-XXXX` or fallback value where applicable).
- Verify delete/action buttons are still aligned and clickable.

## 4) Student Card PDF

Module: Admin documents -> student card print.

- Print/generate one student card PDF.
- Verify student details include `Code Acces` line.
- Verify no PIN or password is printed anywhere on the card.
- Verify layout is readable (no overlap/truncation around added field).

## 5) Student List Report PDF

Module: Student management -> print full list.

- Generate full list PDF.
- Verify header includes `Code Acces` column.
- Verify row data alignment remains correct after new column insertion.
- Verify export/print action completes without runtime error.

## 6) Regression Safety

- Re-run automated QA pack:
  - `pytest tests/test_parent_login_v63.py test_parent_login_e2e.py -q`
- Expected: all tests pass.

## 7) Sign-off

Mark phase closure when all are true:

- [ ] Parent portal manual checks passed.
- [ ] Desktop table manual checks passed.
- [ ] Student card PDF manual checks passed.
- [ ] Student list PDF manual checks passed.
- [ ] Automated pack passed.

Final status template:

- Phase 5.1-5.2 manual QA: PASSED/FAILED
- Blocking issues:
  - None / list of defects
