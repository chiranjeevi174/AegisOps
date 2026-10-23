# AegisOps — Backup, Recovery, and Rollback Procedures (Step 17)

## 1. Overview and Invariants

AegisOps stores operational incident history, evidence references, root cause analyses, approval records, simulation execution details, verifications, and immutable audit events in a persistent PostgreSQL 17 database.

### Core Recovery Invariants
- **Application Image Rollback != Database Migration Rollback:** Reverting a backend container image to a previous release tag does NOT automatically reverse database schema migrations. Schema downgrades must be executed as a deliberate, validated operation.
- **Audit Immutability:** Audit events must never be overwritten, truncated, or dropped during standard operational procedures.
- **Checksum Verification:** All database backups must be accompanied and validated by SHA-256 integrity checksums prior to restoration.

---

## 2. Backup Procedures

### Automated Logical Backup (`scripts/backup_db.py`)
Run the backup script from the workspace root or scheduled cron/task scheduler:
```cmd
uv run python scripts\backup_db.py --container aegisops-prod-postgres --output-dir backups
```

This procedure:
1. Connects to `aegisops-prod-postgres` and invokes `pg_dump` with `--clean --if-exists --no-owner --no-privileges`.
2. Produces a timestamped SQL dump: `backups/aegisops_backup_YYYYMMDD_HHMMSS.sql`.
3. Computes the SHA-256 cryptographic digest and writes `backups/aegisops_backup_YYYYMMDD_HHMMSS.sql.sha256`.
4. Validates that the backup payload is non-empty.

### Backup Verification
To verify the integrity and readability of a backup file without executing a restore:
```cmd
uv run python scripts\backup_db.py --verify-only backups\aegisops_backup_20261022_120000.sql
```

---

## 3. Disaster Recovery & Restoration

### Safe Restoration Tool (`scripts/restore_db.py`)

#### Step A: Dry-Run Simulation
Simulate the restoration check to confirm checksum validity and container availability:
```cmd
uv run python scripts\restore_db.py backups\aegisops_backup_20261022_120000.sql --container aegisops-prod-postgres --dry-run
```

#### Step B: Execute Confirmed Restore
> [!CAUTION]
> Restoring a database drops and recreates existing tables. You must provide `--confirm-overwrite` to authorize this destructive operation. Never run this against active production without taking a pre-restore snapshot.

```cmd
uv run python scripts\restore_db.py backups\aegisops_backup_20261022_120000.sql --container aegisops-prod-postgres --confirm-overwrite
```

---

## 4. Application Release Rollback vs. Database Schema Downgrade

When an application deployment exhibits unexpected behavior, choose the appropriate rollback procedure:

### Scenario 1: Stateless Application Rollback (No Schema Changes)
If the new release did not introduce database migrations:
1. Revert Compose image tag or pull previous stable build:
   ```cmd
   docker compose -p aegisops-prod -f infrastructure\deployment\compose.yaml down backend frontend
   docker compose -p aegisops-prod -f infrastructure\deployment\compose.yaml up -d backend frontend
   ```
2. Verify liveness via `uv run python scripts\verify_deployment.py`.

### Scenario 2: Rollback Involving Database Schema Migrations
If the release applied a new Alembic migration that must be rolled back:
1. **Stop Traffic Ingress:** Stop frontend and backend containers:
   ```cmd
   docker compose -p aegisops-prod -f infrastructure\deployment\compose.yaml stop backend frontend
   ```
2. **Inspect Migration History:** Check current database revision:
   ```cmd
   uv run alembic current
   ```
3. **Execute Controlled Downgrade:** Run Alembic downgrade to the previous stable revision (e.g. `a4cde0ef70ce`):
   ```cmd
   uv run alembic downgrade -1
   ```
4. **Deploy Previous Application Version:** Start backend and frontend on the previous image tag:
   ```cmd
   docker compose -p aegisops-prod -f infrastructure\deployment\compose.yaml up -d backend frontend
   ```
5. **Verify Stack Health:** Run `scripts\verify_deployment.py`.

---

## 5. Docker Volume Persistence & Snapshots

Production data is stored in Docker named volumes:
- `aegisops_prod_postgres_data`
- `aegisops_prod_prometheus_data`
- `aegisops_prod_grafana_data`
- `aegisops_prod_alertmanager_data`

### Volume Backup Example (Host Level)
To create an offline cold snapshot of the PostgreSQL volume:
```cmd
docker run --rm -v aegisops_prod_postgres_data:/volume -v %cd%\backups:/backup alpine tar -czf /backup/postgres_volume_snapshot.tar.gz -C /volume .
```
