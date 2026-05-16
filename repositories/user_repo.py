# repositories/user_repo.py — compatibility shim (real code in src/data/user_repo.py)
from src.data.user_repo import UserRepository  # noqa: F401

__all__ = ['UserRepository']
