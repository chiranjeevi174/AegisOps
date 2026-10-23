import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from aegisops.core.config import get_settings
from aegisops.db.base import Base
from aegisops.domain.approval import RemediationApproval  # noqa: F401
from aegisops.domain.approval_event import ApprovalEvent  # noqa: F401
from aegisops.domain.execution import RemediationExecution  # noqa: F401
from aegisops.domain.execution_event import ExecutionEvent  # noqa: F401
from aegisops.domain.incident import Incident  # noqa: F401
from aegisops.domain.rollback import RollbackAssessment  # noqa: F401
from aegisops.domain.rollback_event import RollbackEvent  # noqa: F401
from aegisops.domain.verification import ExecutionVerification  # noqa: F401
from aegisops.domain.verification_event import VerificationEvent  # noqa: F401

config = context.config

config.set_main_option(
    "sqlalchemy.url",
    get_settings().database_url.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
