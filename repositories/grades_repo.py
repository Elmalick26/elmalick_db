# repositories/grades_repo.py — compatibility shim (real code in src/data/grades_repo.py)
from src.data.grades_repo import GradesRepository  # noqa: F401

__all__ = ['GradesRepository']
