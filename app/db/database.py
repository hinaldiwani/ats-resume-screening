"""
app/db/database.py

Single source of truth for:
  - The SQLAlchemy engine (MySQL connection)
  - The session factory
  - The declarative Base that all models inherit from
  - The get_db() dependency used in FastAPI routes

This consolidates what was split across db/session.py and db/base.py in the
scaffold phase into the conventional "database.py" naming the task asked for.
db/session.py and db/base.py now simply re-export from here so nothing else
in the app breaks.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# pool_pre_ping avoids "MySQL server has gone away" errors on idle connections.
# pool_recycle=3600 forces reconnect every hour, below MySQL's default wait_timeout.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.APP_DEBUG,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
# Every model in app/models.py inherits from this. Alembic's target_metadata
# points here so autogenerate can detect all tables.
Base = declarative_base()


def get_db() -> Session:
    """
    FastAPI dependency — yields a request-scoped DB session and always
    closes it afterward, even if the request raises an exception.

        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
