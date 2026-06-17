"""Alembic environment configuration.

Loads DATABASE_URL from app.config and imports all SQLModel models
so that autogenerate can detect schema changes.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Inject DATABASE_URL from application config ──────────
from app.config import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ── Import all models to register on SQLModel.metadata ───
from sqlmodel import SQLModel  # noqa: E402
from app.models import Movie, ScrapeLog, User  # noqa: E402, F401

target_metadata = SQLModel.metadata


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
