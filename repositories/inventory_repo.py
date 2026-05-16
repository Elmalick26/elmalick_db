# repositories/inventory_repo.py — compatibility shim (real code in src/data/inventory_repo.py)
from src.data.inventory_repo import InventoryRepository  # noqa: F401

__all__ = ['InventoryRepository']
