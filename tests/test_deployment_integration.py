"""Deployment integration tests validating Dockerfiles, Compose syntax, and operational tools."""

import tempfile
from pathlib import Path

from scripts.backup_db import calculate_sha256, verify_backup
from scripts.restore_db import restore_backup


def test_compose_yaml_structure_and_security():
    """Verifies that infrastructure/deployment/compose.yaml satisfies security and service requirements."""
    compose_path = Path("infrastructure/deployment/compose.yaml")
    assert compose_path.is_file(), "infrastructure/deployment/compose.yaml must exist"

    content = compose_path.read_text(encoding="utf-8")

    # Required services must be defined
    required_services = [
        "postgres:",
        "migration:",
        "backend:",
        "frontend:",
        "prometheus:",
        "alertmanager:",
        "grafana:",
    ]
    for srv in required_services:
        assert srv in content, f"Service '{srv}' is missing from compose.yaml"

    # PostgreSQL must NOT expose ports to host
    # Find postgres block and ensure no "5432:5432" or host port mappings
    postgres_block = content.split("migration:")[0]
    assert "ports:" not in postgres_block, (
        "PostgreSQL should not publish ports to host in production compose"
    )

    # Resource constraints must be defined
    assert "limits:" in content, "Compose file must define container resource limits"
    assert "json-file" in content, "Compose file must configure log rotation driver"


def test_backend_dockerfile_security_guidelines():
    """Verifies that the backend Dockerfile follows multi-stage and unprivileged execution rules."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.is_file(), "Root backend Dockerfile must exist"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage build check
    assert "FROM python:3.12-slim-bookworm AS builder" in content
    assert "FROM python:3.12-slim-bookworm AS runtime" in content

    # Non-root user check
    assert "useradd" in content
    assert "USER aegisops:aegisops" in content

    # Clean uv sync without development dependencies
    assert "uv sync --frozen --no-dev" in content

    # Health check
    assert "HEALTHCHECK" in content
    assert "/health/live" in content


def test_frontend_dockerfile_and_nginx_proxy_config():
    """Verifies that the frontend Dockerfile and Nginx configuration satisfy reverse-proxy requirements."""
    dockerfile_path = Path("frontend/Dockerfile")
    nginx_conf_path = Path("frontend/nginx.conf")
    assert dockerfile_path.is_file(), "frontend/Dockerfile must exist"
    assert nginx_conf_path.is_file(), "frontend/nginx.conf must exist"

    df_content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM node:22-alpine AS builder" in df_content
    assert "FROM nginx:1.27-alpine AS runtime" in df_content
    assert "USER nginx" in df_content

    nginx_content = nginx_conf_path.read_text(encoding="utf-8")
    assert "try_files $uri $uri/ /index.html;" in nginx_content, (
        "SPA routing fallback missing"
    )
    assert "proxy_pass http://backend:8000;" in nginx_content, (
        "API proxy pass directive missing"
    )
    assert "client_max_body_size 10M;" in nginx_content, (
        "Request body size limit missing"
    )
    assert "nosniff" in nginx_content, "nosniff security header missing from Nginx"
    assert "DENY" in nginx_content, "DENY clickjacking header missing from Nginx"


def test_backup_and_restore_checksum_validation():
    """Tests checksum calculation and safety guardrails in backup and restore tools."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dummy_backup = tmp_path / "test_backup.sql"
        dummy_backup.write_text("CREATE TABLE test (id INT);", encoding="utf-8")

        # 1. Compute checksum
        sha256_hash = calculate_sha256(dummy_backup)
        assert len(sha256_hash) == 64

        # 2. Write companion checksum file
        checksum_file = dummy_backup.with_suffix(dummy_backup.suffix + ".sha256")
        checksum_file.write_text(
            f"{sha256_hash}  {dummy_backup.name}\n", encoding="utf-8"
        )

        # 3. Verify backup checksum passes
        assert verify_backup(dummy_backup) is True

        # 4. Corrupt checksum and verify it fails
        checksum_file.write_text(
            "0000000000000000000000000000000000000000000000000000000000000000  bad.sql\n",
            encoding="utf-8",
        )
        assert verify_backup(dummy_backup) is False

        # Restore valid checksum for restore verification tests
        checksum_file.write_text(
            f"{sha256_hash}  {dummy_backup.name}\n", encoding="utf-8"
        )

        # 5. Restore utility safety refusal without --confirm-overwrite
        res_refusal = restore_backup(
            backup_file=dummy_backup,
            container_name="test-postgres",
            db_name="test-db",
            confirmed=False,
            dry_run=False,
        )
        assert res_refusal is False, "Restore without confirmation must be refused"

        # 6. Dry run simulation passes
        res_dry_run = restore_backup(
            backup_file=dummy_backup,
            container_name="test-postgres",
            db_name="test-db",
            confirmed=False,
            dry_run=True,
        )
        assert res_dry_run is True


def test_production_env_example_completeness():
    """Verifies that infrastructure/deployment/.env.example covers all required deployment keys."""
    env_example = Path("infrastructure/deployment/.env.example")
    assert env_example.is_file()

    content = env_example.read_text(encoding="utf-8")
    mandatory_vars = [
        "APP_ENV=production",
        "DATABASE_URL=",
        "POSTGRES_PASSWORD=",
        "ALERTMANAGER_WEBHOOK_TOKEN=",
        "CSRF_SECRET_KEY=",
        "GRAFANA_ADMIN_PASSWORD=",
        "ENABLE_DEV_PERSONA_SWITCHING=false",
        "LIVE_DIAGNOSTICS_ENABLED=false",
        "GEMINI_MODEL=",
    ]
    for var in mandatory_vars:
        assert var in content, (
            f"Mandatory variable '{var}' missing from deployment .env.example"
        )
