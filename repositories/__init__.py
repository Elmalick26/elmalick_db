"""Compatibility shim — real code lives in src/data/.

All existing imports (``from repositories.X import Y``) continue to work
unchanged via the per-module shim files.  New code should prefer:

    from src.data.student_repo import StudentRepository

This package will be removed in a future release.
"""
