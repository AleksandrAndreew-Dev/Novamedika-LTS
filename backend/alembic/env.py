"""Alembic environment configuration."""

import asyncio
from logging.config import fileConfig
import os
import sys

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Добавляем src в sys.path (относительно backend/)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_backend_dir, "..", "src")
sys.path.insert(0, _src_dir)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем все модели
from src.db.base import Base
from src.db.models import Pharmacy, Product
from src.db.qa_models import User, Pharmacist, Question, Answer, DialogMessage
from src.db.booking_models import BookingOrder, PharmacyAPIConfig, SyncLog
from src.db.token_models import RefreshToken

# Alembic Config object
config = context.config

# Переопределяем sqlalchemy.url из environment
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
