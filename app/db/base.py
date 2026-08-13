"""
app/db/base.py

Kept for backward compatibility with the earlier scaffold. The declarative
Base now lives in app/db/database.py — this module re-exports it, and also
imports all models so Alembic's autogenerate can discover every table.
"""

from app.db.database import Base  # noqa: F401

# Import all models here so Base.metadata is fully populated for Alembic
# autogenerate and for Base.metadata.create_all() in init_db.py
from app.models import models  # noqa: F401
