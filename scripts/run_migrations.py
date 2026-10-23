"""Controlled Alembic database migration runner for AegisOps production deployment."""

import asyncio
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from aegisops.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegisops.migrations")


async def wait_for_database(
    db_url: str, max_retries: int = 15, delay_seconds: float = 2.0
) -> bool:
    """Verifies that the target PostgreSQL database is accepting connections."""
    engine = create_async_engine(db_url, echo=False)
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Checking database connectivity (attempt %d/%d)...",
                attempt,
                max_retries,
            )
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to database.")
            await engine.dispose()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Database not ready yet: %s. Retrying in %.1fs...", exc, delay_seconds
            )
            await asyncio.sleep(delay_seconds)
    await engine.dispose()
    return False


def run_migrations(ini_path: Path | None = None) -> int:
    """Executes Alembic migrations up to head in a controlled, validated procedure."""
    settings = get_settings()
    logger.info("Target database URL: %s", settings.database_url.split("@")[-1])

    # 1. Verify database is reachable before triggering Alembic
    is_ready = asyncio.run(wait_for_database(settings.database_url))
    if not is_ready:
        logger.error(
            "Failed to connect to database within the timeout period. Migration aborted."
        )
        return 1

    # 2. Locate alembic.ini
    if ini_path is None:
        ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    if not ini_path.is_file():
        logger.error("alembic.ini not found at expected path: %s", ini_path)
        return 1

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option(
        "sqlalchemy.url", settings.database_url.replace("%", "%%")
    )

    try:
        logger.info("Checking current Alembic database revision...")
        command.current(alembic_cfg, verbose=False)

        logger.info("Applying Alembic migrations up to 'head'...")
        command.upgrade(alembic_cfg, "head")

        logger.info("Migrations successfully applied. Verified current revision:")
        command.current(alembic_cfg, verbose=True)
        return 0
    except Exception:
        logger.exception("Alembic migration failed")
        return 1


if __name__ == "__main__":
    exit_code = run_migrations()
    sys.exit(exit_code)
