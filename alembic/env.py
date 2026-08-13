"""
alembic/env.py

Wires Alembic migrations to this project's SQLAlchemy Base and DATABASE_URL
(pulled from app settings rather than duplicated in alembic.ini).

No model metadata is registered yet — target_metadata will pick up models
automatically once they're added to app/db/base.py imports.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os

sys.path.append(os.getcwd())

from app.core.config import get_settings
from app.db.base import Base

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
