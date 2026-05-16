# repositories/attendance_repo.py — compatibility shim (real code in src/data/attendance_repo.py)
from src.data.attendance_repo import AttendanceRepository  # noqa: F401

__all__ = ['AttendanceRepository']
