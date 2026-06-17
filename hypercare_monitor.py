"""
hypercare_monitor.py — مراقبة Hypercare اليومية (7 أيام بعد الإطلاق)

يُشغَّل يدوياً أو بـ Cron كل صباح خلال أسبوع الـ Hypercare:
    python hypercare_monitor.py
    python hypercare_monitor.py --days 3   # تحليل آخر 3 أيام
    python hypercare_monitor.py --save     # حفظ التقرير في school_data/

يخرج بـ exit code:
    0 — كل شيء سليم
    1 — توجد تحذيرات تحتاج مراجعة
    2 — خطأ حرج (P1)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ── force UTF-8 output on Windows terminals ───────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# ── paths ─────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent
_LOGS_DIR = _ROOT / "logs"
_SCHOOL_DATA_DIR = _ROOT / "school_data"
_BACKUPS_DIR = _ROOT / "backups"

# ── thresholds (P1 = critical, P2 = warning) ─────────────────────────────
P1_ERROR_COUNT = 20  # >20 ERROR lines per day → P1
P2_ERROR_COUNT = 5  # >5 ERROR lines per day → P2 warning
P1_NO_BACKUP_HOURS = 25  # no backup in 25 h → P1
P2_NO_BACKUP_HOURS = 13  # no backup in 13 h → P2

# ── result tracking ───────────────────────────────────────────────────────
_issues: list[dict] = []  # {"level": "P1"|"P2"|"INFO", "msg": str}
_max_severity = 0  # 0=ok, 1=P2, 2=P1


def _record(level: str, msg: str) -> None:
    global _max_severity
    _issues.append({"level": level, "msg": msg, "time": datetime.now().isoformat()})
    if level == "P1":
        _max_severity = max(_max_severity, 2)
    elif level == "P2":
        _max_severity = max(_max_severity, 1)


def _ok(msg: str) -> None:
    _issues.append({"level": "OK", "msg": msg, "time": datetime.now().isoformat()})


# ── 1. Log file analysis ──────────────────────────────────────────────────


def analyse_logs(days: int = 1) -> dict:  # noqa: C901
    """Scan app log files for the last `days` day(s)."""
    cutoff = datetime.now() - timedelta(days=days)
    log_files = sorted(_LOGS_DIR.glob("app_*.log"))
    if not log_files:
        _record("P2", f"No log files found in {_LOGS_DIR}")
        return {}

    # Filter files modified within the window
    recent = [p for p in log_files if datetime.fromtimestamp(p.stat().st_mtime) >= cutoff]
    if not recent:
        recent = [log_files[-1]]  # always check at least the latest

    counter: Counter = Counter()
    error_samples: list[str] = []
    module_errors: Counter = Counter()

    _ERROR_RE = re.compile(r"\bERROR\b", re.IGNORECASE)
    _CRITICAL_RE = re.compile(r"\bCRITICAL\b", re.IGNORECASE)
    _MODULE_RE = re.compile(r"\[(\w[\w.]*)\]")

    for log_path in recent:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if _CRITICAL_RE.search(line):
                        counter["CRITICAL"] += 1
                        if len(error_samples) < 5:
                            error_samples.append(line.rstrip())
                        m = _MODULE_RE.search(line)
                        if m:
                            module_errors[m.group(1)] += 1
                    elif _ERROR_RE.search(line):
                        counter["ERROR"] += 1
                        if len(error_samples) < 5:
                            error_samples.append(line.rstrip())
                        m = _MODULE_RE.search(line)
                        if m:
                            module_errors[m.group(1)] += 1
        except OSError as exc:
            _record("P2", f"Cannot read log file {log_path.name}: {exc}")

    total_errors = counter["ERROR"] + counter["CRITICAL"]
    result = {
        "files_scanned": [p.name for p in recent],
        "total_errors": total_errors,
        "critical": counter["CRITICAL"],
        "errors": counter["ERROR"],
        "top_modules": dict(module_errors.most_common(5)),
        "error_samples": error_samples,
    }

    if counter["CRITICAL"] > 0:
        _record(
            "P1",
            f"{counter['CRITICAL']} CRITICAL entries found — " f"top modules: {dict(module_errors.most_common(3))}",
        )
    elif total_errors >= P1_ERROR_COUNT:
        _record("P1", f"{total_errors} ERRORs in last {days} day(s) " f"(threshold: {P1_ERROR_COUNT})")
    elif total_errors >= P2_ERROR_COUNT:
        _record("P2", f"{total_errors} ERRORs in last {days} day(s) " f"(threshold: {P2_ERROR_COUNT})")
    else:
        _ok(f"Log errors: {total_errors} — within normal range")

    return result


# ── 2. Backup freshness check ─────────────────────────────────────────────


def check_backup_freshness() -> dict:
    """Verify that at least one backup exists and is recent."""
    sql_files = sorted(_BACKUPS_DIR.glob("*.sql"))
    backup_files = sorted(_BACKUPS_DIR.glob("*.backup"))
    all_backups = sql_files + backup_files

    if not all_backups:
        _record("P1", f"No backup files found in {_BACKUPS_DIR}")
        return {"count": 0, "latest": None, "age_hours": None}

    latest = max(all_backups, key=lambda p: p.stat().st_mtime)
    age_seconds = time.time() - latest.stat().st_mtime
    age_hours = round(age_seconds / 3600, 1)

    result = {
        "count": len(all_backups),
        "latest": latest.name,
        "age_hours": age_hours,
    }

    if age_hours >= P1_NO_BACKUP_HOURS:
        _record("P1", f"Latest backup is {age_hours}h old " f"(threshold: {P1_NO_BACKUP_HOURS}h): {latest.name}")
    elif age_hours >= P2_NO_BACKUP_HOURS:
        _record("P2", f"Latest backup is {age_hours}h old " f"(threshold: {P2_NO_BACKUP_HOURS}h): {latest.name}")
    else:
        _ok(f"Backup OK — latest: {latest.name} ({age_hours}h ago)")

    return result


# ── 3. API health check (optional — requires running server) ──────────────


def check_api_health(base_url: str) -> dict | None:
    """Call /api/health and record any issues. Returns None if server unreachable."""
    try:
        try:
            import httpx

            resp = httpx.get(f"{base_url}/api/health", timeout=5.0)
        except ImportError:
            import requests  # type: ignore

            resp = requests.get(f"{base_url}/api/health", timeout=5.0)

        if resp.status_code != 200:
            _record("P1", f"/api/health returned HTTP {resp.status_code}")
            return {"status_code": resp.status_code}

        body = resp.json()
        result = {
            "status": body.get("status"),
            "db_latency_ms": body.get("db_latency_ms"),
            "db_size": body.get("db_size"),
            "last_backup": body.get("last_backup"),
            "pool": body.get("pool"),
        }

        if body.get("status") != "ok":
            _record("P1", f"/api/health status={body.get('status')!r}")
        elif body.get("db_latency_ms", 0) > 500:
            _record("P2", f"DB latency high: {body['db_latency_ms']} ms (threshold: 500)")
        else:
            pool = body.get("pool", {})
            util = pool.get("utilization_pct", 0)
            if util >= 80:
                _record("P2", f"Connection pool at {util}% utilization")
            else:
                _ok(f"API health OK — latency {body.get('db_latency_ms')} ms, " f"pool {util}%")
        return result

    except Exception as exc:
        # Server may not be running in dev — treat as INFO, not P1
        _ok(f"API server not reachable (offline check): {exc}")
        return None


# ── 4. Disk space check ───────────────────────────────────────────────────


def check_disk_space() -> dict:
    """Warn if log dir or project dir is on low-disk volume (Windows + Unix)."""
    try:
        import shutil

        stat = shutil.disk_usage(_ROOT)
        free_gb = round(stat.free / 1024**3, 2)
        total_gb = round(stat.total / 1024**3, 2)
        pct_used = round((stat.used / stat.total) * 100, 1)
        result = {"free_gb": free_gb, "total_gb": total_gb, "pct_used": pct_used}
        if free_gb < 1.0:
            _record("P1", f"Disk critically low: {free_gb} GB free on {_ROOT.drive or _ROOT}")
        elif free_gb < 5.0:
            _record("P2", f"Disk space low: {free_gb} GB free ({pct_used}% used)")
        else:
            _ok(f"Disk OK — {free_gb} GB free ({pct_used}% used)")
        return result
    except Exception as exc:
        _ok(f"Disk check skipped: {exc}")
        return {}


# ── report ────────────────────────────────────────────────────────────────


def _build_report(log_result: dict, backup_result: dict, api_result: dict | None, disk_result: dict, days: int) -> dict:
    severity_map = {0: "GREEN", 1: "YELLOW", 2: "RED"}
    return {
        "generated_at": datetime.now().isoformat(),
        "analysis_window_days": days,
        "overall_severity": severity_map[_max_severity],
        "issues": _issues,
        "details": {
            "logs": log_result,
            "backup": backup_result,
            "api_health": api_result,
            "disk": disk_result,
        },
    }


def _print_report(report: dict) -> None:
    severity = report["overall_severity"]
    icons = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
    icon = icons.get(severity, "⚪")

    print(f"\n{'═' * 65}")
    print("  El Malick Gest — Hypercare Daily Report")
    print(f"  {report['generated_at']}  |  window: {report['analysis_window_days']} day(s)")
    print(f"  Overall: {icon} {severity}")
    print(f"{'═' * 65}")

    for item in report["issues"]:
        lvl = item["level"]
        if lvl == "OK":
            print(f"  ✅  {item['msg']}")
        elif lvl == "P2":
            print(f"  ⚠️   P2 — {item['msg']}")
        elif lvl == "P1":
            print(f"  🔴  P1 — {item['msg']}")

    # Quick stats
    d = report["details"]
    if d.get("logs"):
        print(f"\n  Log errors (last {report['analysis_window_days']}d): " f"{d['logs'].get('total_errors', '?')}")
    if d.get("backup") and d["backup"].get("latest"):
        print(f"  Latest backup : {d['backup']['latest']} " f"({d['backup'].get('age_hours')}h ago)")
    if d.get("disk"):
        print(f"  Disk free     : {d['disk'].get('free_gb')} GB")
    print(f"{'═' * 65}\n")


# ── entry point ───────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="El Malick Gest — Hypercare Monitoring")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back in logs (default: 1)")
    parser.add_argument(
        "--url",
        default=os.environ.get("ELMALICK_BASE_URL", "http://localhost:8000"),
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--save", action="store_true", help="Save JSON report to school_data/")
    args = parser.parse_args()

    log_result = analyse_logs(args.days)
    backup_result = check_backup_freshness()
    api_result = check_api_health(args.url)
    disk_result = check_disk_space()

    report = _build_report(log_result, backup_result, api_result, disk_result, args.days)
    _print_report(report)

    if args.save:
        _SCHOOL_DATA_DIR.mkdir(exist_ok=True)
        out = _SCHOOL_DATA_DIR / f"hypercare_{datetime.now().strftime('%Y-%m-%d')}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Report saved → {out.relative_to(_ROOT)}\n")

    return _max_severity  # 0=ok, 1=P2 warning, 2=P1 critical


if __name__ == "__main__":
    sys.exit(main())
