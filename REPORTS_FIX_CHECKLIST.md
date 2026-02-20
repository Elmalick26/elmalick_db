# Reports Fix Checklist

## Scope

This checklist defines the mandatory quality rules for reports across the application.

## P0 — Data Accuracy (Mandatory)

- All report queries must be scoped by `period_id` and/or `year_id` whenever the schema supports it.
- If historical rows exist without `year_id`, code may fallback only when no year-scoped rows are found.
- Ranking shown in UI must match ranking used in generated bulletin output.

## P1 — Report UX Integrity

- UI controls must have real effect on query output (no dead filters).
- Any not-yet-implemented export option must be disabled or hidden.

## P2 — PDF Reliability

- PDF export must use Save dialog (no silent overwrite).
- Default filenames should include timestamp.
- Arabic text fallback must preserve readable text where possible (not just `...`).

## Validation Rules Before Merge

- No diagnostics errors in modified files.
- Verify at least one class report path:
  - Batch result ranking
  - Individual bulletin ranking
  - Honor roll ranking
  must be consistent for the same period.
- Verify financial chart responds to all period options.
- Verify receipt and late-payers PDF save to user-selected path.

## Changed in Current Iteration

- `bulletin_generation.py`
  - Year-aware score lookup.
  - Year-aware attendance/discipline retrieval with fallback.
  - Final ranking unified with conduct (used in batch, individual, bulletins, honor roll).
- `advanced_reports.py`
  - Financial period selector now drives SQL filtering.
  - Attendance and grades exports implemented and wired to UI actions.
  - Student performance chart filtered by active year with legacy fallback and year label display.
  - Students Excel export scoped to active year (via StudentClassNumbers) with fallback when legacy data is used.
  - Excel filenames for students/attendance/grades/financial exports are collision-safe (microsecond timestamp).
  - Excel export flow now uses SaveDialog so users choose output path before generation.
- `database_setup.py`
  - Added reporting-focused indexes for year/period/date filtered queries (attendance, discipline, periods, payments, expenses, student-class mapping).
- `finance_payments.py`
  - Save dialogs and timestamped defaults for receipts and late-payers PDF.
- `student_management.py`
  - Better Arabic PDF fallback text.
  - Arabic font detection expanded to `Fonts/` paths.
