from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context
from app import models  # noqa: F401  (register tables on Base.metadata)
from app.config import settings
from app.db import Base

MIGRATION_LOCK_KEY = 7_364_025  # arbitrary, unique to ClinicFlow migrations

config = context.config
# configparser treats % as interpolation, so URL-encoded passwords must be escaped
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            if connection.dialect.name == "postgresql":
                # Every backend replica runs migrations on start. The transaction-scoped advisory lock makes
                # them take turns: the first migrates, the others wait, then find the schema already at head.
                connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK_KEY})
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
