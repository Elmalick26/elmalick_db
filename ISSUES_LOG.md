# El Malick Gest v2.0.0-rc1 — P1/P2 Issues Log

**Version**: v2.0.0-rc1
**Launch date**: (to be filled on launch day)
**Hypercare window**: 7 days post-launch
**Last updated**: 2026-05-25

---

## SLAs

| Severity | Definition | Response | Resolution |
|----------|-----------|----------|------------|
| **P1** | Data loss / security breach / total service outage | ≤ 15 min | ≤ 24 h |
| **P2** | Major feature broken / performance degraded | ≤ 2 h | ≤ 72 h |
| **P3** | Minor bug / UI issue / cosmetic | ≤ 1 day | next sprint |

---

## Open Issues

_No open issues at this time._

<!-- Template for new issues:
| ID | Severity | Title | Reported | Assigned | Status | Resolution |
|----|----------|-------|----------|----------|--------|------------|
| #001 | P1 | short description | YYYY-MM-DD HH:MM | owner | Open | — |
-->

---

## Closed Issues

_No closed issues at this time._

---

## Issue Detail Template

```
### #NNN — [P1/P2] Short title

- **Severity**: P1 / P2
- **Reported**: YYYY-MM-DD HH:MM
- **Reporter**: name / monitoring system
- **Assigned**: name
- **Status**: Open / In Progress / Closed

**Symptoms**:
(describe what the user/monitor observed)

**Root cause**:
(filled after investigation)

**Fix applied**:
(commit / migration / config change)

**Closed**: YYYY-MM-DD HH:MM
**Verified by**: name
```

---

## Hypercare Daily Summaries

| Day | Date | Severity | Error Count | Backup Age | Notes |
|-----|------|----------|-------------|------------|-------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |

> Fill daily from: `python hypercare_monitor.py --save`
> Report files: `school_data/hypercare_YYYY-MM-DD.json`

---

## Escalation Contacts

| Severity | Contact | Method | Availability |
|----------|---------|--------|-------------|
| P1 | Tech Lead | Phone + Signal | 24/7 during Hypercare |
| P1 | Database Admin | Phone | 24/7 during Hypercare |
| P2 | Developer on call | Signal | Business hours |
| Any | Support channel | Signal group | 08:00–20:00 |

> See full contact list in [RUNBOOK.md](RUNBOOK.md) §6.
