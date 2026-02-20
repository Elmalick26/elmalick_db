# Reports Commit Sequence

## Current state

- Repository status: `No commits yet`.
- `Bundle 1` is already staged:
  - `advanced_reports.py`
  - `bulletin_generation.py`

## Important note

- Because there is no initial commit, files are currently added as full new files.
- Splitting the *same new file* (especially `advanced_reports.py`) into multiple semantic commits is limited unless:
  - you create a first baseline commit, then apply focused follow-up commits, or
  - you manually split with advanced patch workflows.

## Commit 1 (Report accuracy + filtering)

```powershell
git commit -m "reports: fix year/period filtering and ranking consistency"
```

## Commit 2 (Practical path from current state)

```powershell
git add finance_payments.py student_management.py
git commit -m "reports: improve save dialogs, paths, and filename reliability"
```

## Commit 3 (DB performance + checklist)

```powershell
git add database_setup.py REPORTS_FIX_CHECKLIST.md
git commit -m "reports: add reporting indexes and update fix checklist"
```

## Optional cleanup before push (generated artifacts)

```powershell
# remove generated test artifacts from git consideration (keep files on disk)
# choose only if needed:
# git clean -nd  # preview untracked
# git clean -fd  # delete untracked files/folders
```
