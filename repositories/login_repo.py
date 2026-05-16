# repositories/login_repo.py — compatibility shim (real code in src/data/login_repo.py)
from src.data.login_repo import LoginRepository  # noqa: F401

__all__ = ['LoginRepository']
