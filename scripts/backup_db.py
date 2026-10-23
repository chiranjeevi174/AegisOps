"""Logical PostgreSQL backup script for AegisOps containerized deployment."""

import argparse
import hashlib
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegisops.backup")


def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_backup(
    output_dir: Path,
    container_name: str = "aegisops-prod-postgres",
    db_name: str = "aegisops",
    db_user: str = "aegisops",
) -> Path | None:
    """Creates a logical database backup via docker exec pg_dump."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"aegisops_backup_{timestamp}.sql"
    checksum_file = output_dir / f"aegisops_backup_{timestamp}.sql.sha256"

    cmd = [
        "docker",
        "exec",
        "-i",
        container_name,
        "pg_dump",
        "-U",
        db_user,
        "-d",
        db_name,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
    ]

    logger.info("Executing database dump from container '%s'...", container_name)
    try:
        with open(backup_file, "wb") as f:
            proc = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                check=False,
            )

        if proc.returncode != 0:
            stderr_msg = proc.stderr.decode("utf-8", errors="replace")
            logger.error(
                "pg_dump failed with exit code %d: %s", proc.returncode, stderr_msg
            )
            if backup_file.exists():
                backup_file.unlink()
            return None

        # Verify backup file size
        file_size = backup_file.stat().st_size
        if file_size == 0:
            logger.error("Backup file was generated with 0 bytes. Aborting.")
            backup_file.unlink()
            return None

        sha256_hash = calculate_sha256(backup_file)
        checksum_file.write_text(
            f"{sha256_hash}  {backup_file.name}\n", encoding="utf-8"
        )

        logger.info(
            "Backup successfully completed!\nFile: %s\nSize: %d bytes\nSHA-256: %s",
            backup_file,
            file_size,
            sha256_hash,
        )
        return backup_file

    except Exception:
        logger.exception("Unexpected error during backup creation")
        if backup_file.exists():
            backup_file.unlink()
        return None


def verify_backup(backup_file: Path) -> bool:
    """Verifies that a backup file exists, is non-empty, and matches its SHA-256 checksum."""
    if not backup_file.is_file():
        logger.error("Backup file '%s' does not exist.", backup_file)
        return False

    checksum_file = backup_file.with_suffix(backup_file.suffix + ".sha256")
    if not checksum_file.is_file():
        logger.warning(
            "No companion .sha256 checksum file found for '%s'.", backup_file
        )
        return backup_file.stat().st_size > 0

    expected_hash = checksum_file.read_text(encoding="utf-8").strip().split()[0]
    actual_hash = calculate_sha256(backup_file)

    if expected_hash.lower() == actual_hash.lower():
        logger.info(
            "SHA-256 checksum verification PASSED for '%s' (%s).",
            backup_file.name,
            actual_hash,
        )
        return True
    else:
        logger.error(
            "Checksum mismatch for '%s'! Expected: %s, Actual: %s",
            backup_file.name,
            expected_hash,
            actual_hash,
        )
        return False


def main():
    parser = argparse.ArgumentParser(description="AegisOps Database Backup Tool")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backups"),
        help="Directory where backup SQL files are saved (default: backups/)",
    )
    parser.add_argument(
        "--container",
        default="aegisops-prod-postgres",
        help="PostgreSQL Docker container name (default: aegisops-prod-postgres)",
    )
    parser.add_argument(
        "--db-name",
        default="aegisops",
        help="Database name to back up (default: aegisops)",
    )
    parser.add_argument(
        "--db-user",
        default="aegisops",
        help="Database user (default: aegisops)",
    )
    parser.add_argument(
        "--verify-only",
        type=Path,
        default=None,
        help="Verify the integrity and checksum of an existing backup file without dumping",
    )

    args = parser.parse_args()

    if args.verify_only:
        success = verify_backup(args.verify_only)
        sys.exit(0 if success else 1)

    result = create_backup(
        output_dir=args.output_dir,
        container_name=args.container,
        db_name=args.db_name,
        db_user=args.db_user,
    )
    sys.exit(0 if result is not None else 1)


if __name__ == "__main__":
    main()
