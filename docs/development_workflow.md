# AegisOps — Local Development & Operational Workflow

This guide details the streamlined development workflow using the AegisOps Development Lifecycle Manager (`scripts/dev.py`).

---

## 1. Daily Development Workflow

Instead of launching multiple manual terminal windows or diagnosing port conflicts, use `scripts/dev.py`:

### Quickstart Commands

```cmd
:: 1. Navigate to project root
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps"

:: 2. Pre-flight verification (tools, ports, env files)
uv run python scripts/dev.py check

:: 3. Start development environment (idempotent, reuses healthy services)
uv run python scripts/dev.py start

:: 4. View active service status and endpoints
uv run python scripts/dev.py status
```

---

## 2. Service Endpoints

Once started, the following services are available:

| Service | URL | Default Credentials / Context | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend Dashboard** | `http://localhost:5173` | Authenticated as `sre-operator-dan` | Incident management, telemetry, approvals, audit |
| **FastAPI Swagger UI** | `http://localhost:8000/docs` | Built-in Swagger UI | Interactive API exploration |
| **Prometheus UI** | `http://localhost:9090` | N/A | Metrics explorer, targets, alert rules |
| **Grafana UI** | `http://localhost:3000` | User: `admin`, Password in `.env` | Provisioned SRE dashboards & availability |
| **Alertmanager UI** | `http://localhost:9093` | N/A | Alert routing and receiver status |
| **Telemetry Simulator**| `http://127.0.0.1:8001/metrics`| N/A | Simulated service telemetry provider |

---

## 3. Command Reference

### `uv run python scripts/dev.py check`
Validates:
- Workspace files (`.env`, `infrastructure/compose.yaml`, etc.)
- CLI prerequisites (`docker`, `uv`, `node`, `npm`)
- Docker Engine availability
- Port availability across all 7 development ports (8000, 8001, 5173, 5433, 9090, 3000, 9093)
- Synchronizes `infrastructure/.env` from `.env` if missing

### `uv run python scripts/dev.py start`
Idempotently starts all development components in the correct dependency order:
1. Starts Docker containers (`aegisops-postgres`, `aegisops-prometheus`, `aegisops-grafana`, `aegisops-alertmanager`)
2. Waits for PostgreSQL readiness
3. Executes Alembic database migrations (`uv run alembic upgrade head`)
4. Starts the telemetry simulator on port 8001 (reuses existing if healthy)
5. Starts the FastAPI backend with Uvicorn reload on port 8000 (reuses existing if healthy, preventing `[WinError 10013]`)
6. Starts the React Vite frontend dev server on port 5173 (reuses existing if healthy)

### `uv run python scripts/dev.py status`
Queries and reports live operational health:
- Docker container states and port mappings
- Endpoint HTTP status codes (`/health/live`, `/health/ready`, `/docs`, `/metrics`, etc.)
- Prometheus scrape target states (`aegisops-api` and `aegisops-simulator`)
- Tracked process PIDs

### `uv run python scripts/dev.py stop [--docker]`
Safely stops development processes:
- Only terminates tracked development processes (`uvicorn`, `simulate_service`, `vite`) after validating their command lines
- Never terminates unrelated Windows processes
- Preserves Docker named volumes and database contents intact
- Pass `--docker` to also stop Docker containers (`docker compose stop`)

### `uv run python scripts/dev.py doctor`
Deep diagnostics for common developer issues:
- Verifies `.env` and `infrastructure/.env` integrity
- Checks port bindings and socket conflicts
- Validates database connectivity and Alembic head
- Validates end-to-end telemetry pipeline (simulator -> Prometheus -> `/api/v1/overview/telemetry`)
- Inspects backend readiness and dependency latencies

---

## 4. Troubleshooting Common Issues

### Issue: `[WinError 10013] An attempt was made to access a socket...`
- **Cause**: Port 8000 is already bound exclusively by an existing Uvicorn instance.
- **Solution**: Run `uv run python scripts/dev.py start`. The lifecycle manager detects existing healthy instances and reuses them without conflict. To stop the existing instance, run `uv run python scripts/dev.py stop`.

### Issue: `Prometheus: Local Standby` in Dashboard
- **Cause**: Telemetry simulator is stopped, leaving `aegisops_sim_service_up` metric unavailable.
- **Solution**: Run `uv run python scripts/dev.py start`. The simulator will launch automatically and Prometheus will resume scraping within 15 seconds.

### Issue: `GRAFANA_ADMIN_PASSWORD is missing a value`
- **Cause**: Docker Compose looks for `.env` in the compose directory (`infrastructure/`).
- **Solution**: `scripts/dev.py` automatically synchronizes `infrastructure/.env` from root `.env` during `check` and `start`.
