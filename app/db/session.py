"""
app/db/session.py

Kept for backward compatibility with the earlier scaffold. The real
implementation now lives in app/db/database.py — this module just re-exports
so any existing `from app.db.session import get_db` imports keep working.
"""

from app.db.database import engine, SessionLocal, get_db  # noqa: F401
