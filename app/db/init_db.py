"""
app/db/init_db.py

Placeholder for database initialization (e.g., creating tables in dev,
seeding lookup data). Left intentionally empty of logic until the
models/services layers are built.
"""

from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    """
    Dev-only convenience function to create tables directly from models
    without Alembic. In production, migrations (Alembic) should be the
    only source of schema changes — this function should not be called
    outside local development.
    """
    Base.metadata.create_all(bind=engine)
