from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

Base = declarative_base()

def create_database_if_not_exists():
    """Ensure target MySQL database exists."""
    try:
        engine_base = create_engine(settings.BASE_DATABASE_URL, echo=False)
        with engine_base.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
            conn.commit()
    except Exception as e:
        print(f"Database creation check warning: {e}")

create_database_if_not_exists()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

def ensure_database_schema():
    """Ensure newly added columns exist in MySQL tables without breaking existing records."""
    try:
        from sqlalchemy import inspect
        insp = inspect(engine)
        if "screening_results" in insp.get_table_names():
            existing_cols = {c["name"] for c in insp.get_columns("screening_results")}
            new_columns = [
                ("detected_experience", "VARCHAR(100) NULL"),
                ("detected_education", "VARCHAR(255) NULL"),
                ("job_keywords_json", "TEXT NULL"),
                ("explanation", "TEXT NULL"),
            ]
            with engine.connect() as conn:
                for col_name, col_def in new_columns:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE `screening_results` ADD COLUMN `{col_name}` {col_def};"))
                        conn.commit()
    except Exception as e:
        print(f"Schema migration warning: {e}")

ensure_database_schema()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
