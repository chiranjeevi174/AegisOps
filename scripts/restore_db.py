"""Safe PostgreSQL database restoration utility for AegisOps containerized deployment."""

import argparse
import hashlib
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegisops.restore")


def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def restore_backup(
    backup_file: Path,
    container_name: str = "aegisops-prod-postgres",
    db_name: str = "aegisops",
    db_user: str = "aegisops",
    dry_run: bool = False,
    confirmed: bool = False,
) -> bool:
    """Safely restores a PostgreSQL SQL dump file into the specified database container."""
    if not backup_file.is_file():
        logger.error("Backup file '%s' does not exist.", backup_file)
        return False

    # 1. Verify companion checksum if available
    checksum_file = backup_file.with_suffix(backup_file.suffix + ".sha256")
    if checksum_file.is_file():
        expected_hash = checksum_file.read_text(encoding="utf-8").strip().split()[0]
        actual_hash = calculate_sha256(backup_file)
        if expected_hash.lower() != actual_hash.lower():
            logger.error(
                "Integrity check failed: Checksum mismatch for '%s'!", backup_file
            )
            return False
        logger.info("SHA-256 checksum verified (%s).", actual_hash)
    else:
        logger.warning("No companion .sha256 found. Proceeding with caution.")

    if dry_run:
        logger.info(
            "[DRY-RUN] Would execute restore of '%s' (%d bytes) into database '%s' in container '%s'.",
            backup_file.name,
            backup_file.stat().st_size,
            db_name,
            container_name,
        )
        return True

    if not confirmed:
        logger.error(
            "SAFETY REFUSAL: Restoring a database will overwrite existing schema and data in '%s'. "
            "You must supply '--confirm-overwrite' to proceed.",
            db_name,
        )
        return False

    cmd = [
        "docker",
        "exec",
        "-i",
        container_name,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
    ]

    logger.info("Restoring database '%s' from '%s'...", db_name, backup_file)
    try:
        with open(backup_file, "rb") as f:
            proc = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                check=False,
            )

        if proc.returncode != 0:
            stderr_msg = proc.stderr.decode("utf-8", errors="replace")
            logger.error(
                "psql restore failed with code %d: %s", proc.returncode, stderr_msg
            )
            return False

        logger.info(
            "Database '%s' was successfully restored from '%s'.",
            db_name,
            backup_file.name,
        )
        return True

    except Exception:
        logger.exception("Failed to execute restore")
        return False


def main():
    parser = argparse.ArgumentParser(description="AegisOps Database Restore Tool")
    parser.add_argument(
        "backup_file", type=Path, help="Path to SQL dump file to restore"
    )
    parser.add_argument(
        "--container",
        default="aegisops-prod-postgres",
        help="PostgreSQL Docker container name (default: aegisops-prod-postgres)",
    )
    parser.add_argument(
        "--db-name",
        default="aegisops",
        help="Target database name (default: aegisops)",
    )
    parser.add_argument(
        "--db-user",
        default="aegisops",
        help="Database user (default: aegisops)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the restoration check without executing any commands",
    )
    parser.add_argument(
        "--confirm-overwrite",
        action="store_true",
        help="Explicit acknowledgement required to overwrite existing database state",
    )

    args = parser.parse_args()
    success = restore_backup(
        backup_file=args.backup_file,
        container_name=args.container,
        db_name=args.db_name,
        db_user=args.db_user,
        dry_run=args.dry_run,
        confirmed=args.confirm_overwrite,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
