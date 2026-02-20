# Release Notes — Reports Stabilization

Date: 2026-02-20
Scope: Academic and financial reports reliability, export consistency, and database performance.

## Highlights

- Fixed year/period filtering logic in report generation to align displayed data with selected context.
- Unified ranking behavior in bulletin generation so conduct/discipline impact is applied consistently.
- Enabled and stabilized advanced exports for attendance and grades where options were previously incomplete.
- Improved export reliability with save dialogs and safer output naming to avoid accidental overwrites.
- Added reporting-focused database indexes to improve performance of frequent report queries.

## Functional Outcomes

- Bulletin and report outputs now reflect active academic year and selected period behavior more accurately.
- Financial chart/export period selection is now effective and reflected in output naming/content.
- Excel export operations are more user-controlled (save path) and collision-resistant (unique filenames).
- PDF save behavior in payment workflows is more predictable for end users.

## Commits Included

- `5c76330` — reports: fix year/period filtering and ranking consistency
- `9199b25` — reports: improve save dialogs, paths, and filename reliability
- `78e3615` — reports: add reporting indexes and update fix checklist
- `80e3b4e` — chore: ignore generated reports and python cache
- `f2d131f` — chore: initial project import (core modules, assets, and configuration)

## Operational Notes

- Working tree is clean at handoff.
- Runtime/generated artifacts are now ignored via `.gitignore` patterns.
- This release focuses on report correctness, export UX reliability, and DB-side performance improvements.
