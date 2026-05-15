"""api/limiter.py — shared rate limiter instance (avoids circular imports)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# يُستورد في main.py (لربطه بالتطبيق) وفي auth.py / routes_parent.py (للـ decorators)
limiter = Limiter(key_func=get_remote_address)
