# repositories/student_repo.py — compatibility shim (real code in src/data/student_repo.py)
from src.data.student_repo import StudentRepository  # noqa: F401

__all__ = ['StudentRepository']
