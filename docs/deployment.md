# AegisOps — Production-Oriented Deployment Guide (Step 17)

## 1. Architecture Overview

AegisOps is deployed as a single-server, containerized micro-service stack orchestrated via Docker Compose (`infrastructure/deployment/compose.yaml`).

```
[ Client / Browser ]
        │  (HTTP / HTTPS Port 8080)
        ▼
[ Nginx Reverse Proxy & Frontend SPA ] (aegisops-prod-frontend)
        │
        ├──► Static Assets & React SPA Router Fallback (/ & /assets/*)
        │
        └──► Reverse Proxy API requests (/api/*)
                 │
                 ▼
     [ FastAPI Backend Core ] (aegisops-prod-backend:8000)
                 │
                 ├──► PostgreSQL 17 (aegisops-prod-postgres:5432 - Internal Only)
                 ├──► Prometheus 3.5 (aegisops-prod-prometheus:9090)
                 └──► Google Gemini API (External HTTPS)

[ Observability Subsystem ] (Admin / SRE Ports)
  ├── Prometheus Metrics Scraper: Port 9091 (scrapes backend:8000/metrics)
  ├── Alertmanager: Port 9094 (dead-letter loop-prevention routing)
  └── Grafana Dashboard: Port 3001 (provisioned AegisOps Platform Overview)
```

### Key Security & Network Properties
1. **Isolated Database:** PostgreSQL is strictly connected to `aegisops-prod-net` and does NOT expose port 5432 to the host or internet.
2. **Same-Origin Reverse Proxy:** Nginx unifies frontend static serving and `/api/` routing on port 8080, mitigating cross-origin complexity while applying strict security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`).
3. **Controlled Pre-Flight Migrations:** The `migration` service executes `scripts/run_migrations.py` before the backend container starts, ensuring database schema readiness without race conditions.

---

## 2. Prerequisites

- **Docker Engine:** v24.0+ / Docker Compose v2.20+
- **Host Ports Available:**
  - `8080` (AegisOps Web Application)
  - `9091` (Prometheus Admin Console)
  - `3001` (Grafana Dashboards)
  - `9094` (Alertmanager Console)
- **Host Architecture:** Windows (CMD/PowerShell), Linux (x86_64/arm64), or macOS.

---

## 3. Environment Configuration

1. Navigate to the deployment infrastructure directory:
   ```cmd
   cd infrastructure\deployment
   ```

2. Copy the deployment environment template:
   ```cmd
   copy .env.example .env
   ```

3. Configure mandatory environment variables in `.env`:
   - `POSTGRES_PASSWORD`: Strong, randomly generated database password (min 16 characters).
   - `DATABASE_URL`: `postgresql+asyncpg://aegisops:<YOUR_POSTGRES_PASSWORD>@postgres:5432/aegisops`
   - `ALERTMANAGER_WEBHOOK_TOKEN`: High-entropy token for Alertmanager webhook authentication.
   - `CSRF_SECRET_KEY`: Cryptographically random secret key (min 32 characters) for HMAC session token binding.
   - `GRAFANA_ADMIN_PASSWORD`: Strong password for Grafana `admin` user.
   - `GEMINI_API_KEY`: Production Google Gemini API key.
   - `GEMINI_MODEL`: Default `gemini-3.5-flash-lite`.
   - `ENABLE_DEV_PERSONA_SWITCHING`: Strictly set to `false`.
   - `LIVE_DIAGNOSTICS_ENABLED`: Set to `false` (default safe mode).

---

## 4. Deployment Execution

### Step A: Build Container Images
Build both backend and frontend images from their multi-stage Dockerfiles:
```cmd
docker compose --env-file infrastructure\deployment\.env -f infrastructure\deployment\compose.yaml build
```

### Step B: Launch Containers
Start the services in detached mode with isolated project name `aegisops-prod`:
```cmd
docker compose -p aegisops-prod --env-file infrastructure\deployment\.env -f infrastructure\deployment\compose.yaml up -d
```

### Step C: Verify Container Startup Order
The Compose orchestration enforces:
1. `postgres` starts and completes healthy verification (`pg_isready`).
2. `migration` executes `scripts/run_migrations.py` and exits with code 0 (`service_completed_successfully`).
3. `backend` starts, connects to PostgreSQL, and passes `/health/live`.
4. `frontend` starts, connects to backend, and serves web traffic.
5. `prometheus`, `grafana`, and `alertmanager` start and begin metric collection.

---

## 5. Deployment Verification

Execute the Windows CMD-compatible verification script:
```cmd
uv run python scripts\verify_deployment.py --base-url http://127.0.0.1:8080 --prometheus-url http://127.0.0.1:9091 --grafana-url http://127.0.0.1:3001 --alertmanager-url http://127.0.0.1:9094
```

Expected verification output:
- **Backend Liveness:** HTTP 200 OK
- **Backend Readiness:** HTTP 200 OK (PostgreSQL & Prometheus verified)
- **Frontend Availability:** HTTP 200 OK (React SPA served)
- **Security Headers:** Present (`nosniff`, `DENY`, `no-store`)
- **Production Persona Gating:** HTTP 403 Forbidden (development impersonation blocked)
- **Database Port Isolation:** Port 5432 closed to external host connections
- **Monitoring Stack:** Prometheus, Grafana, Alertmanager operational
- **Incident & Audit Persistence:** Persistent named volumes verified

---

## 6. Secret Rotation Procedure

When rotating application credentials:
1. **CSRF Secret Key (`CSRF_SECRET_KEY`):** Update in `.env` and restart backend (`docker compose -p aegisops-prod restart backend`). Existing active cookie sessions will be invalidated and re-authenticated on next login.
2. **Alertmanager Token (`ALERTMANAGER_WEBHOOK_TOKEN`):** Update `.env` and `infrastructure/alertmanager/webhook_token.txt`, then reload Alertmanager and backend.
3. **Database Password (`POSTGRES_PASSWORD`):**
   - Alter password in PostgreSQL: `ALTER USER aegisops WITH PASSWORD 'new_pass';`
   - Update `POSTGRES_PASSWORD` and `DATABASE_URL` in `.env`.
   - Restart stack: `docker compose -p aegisops-prod up -d`.

---

## 7. Public-Deployment Prerequisites

> [!WARNING]
> This deployment configuration is classified as a **Restricted production-like / private evaluation environment**.
> It is NOT intended for direct, unrestricted public internet exposure without fulfilling the following prerequisites:
> 1. **Enterprise Identity Provider (OIDC / SAML):** Integrate an organizational IdP (Okta, Keycloak, or Google Workspace) to replace token/session-based human authentication.
> 2. **TLS / SSL Termination:** Terminate HTTPS via a corporate reverse proxy (e.g. Cloudflare, AWS ALB, or certbot/Let's Encrypt Nginx) and configure `session_cookie_secure=True` and `enable_hsts=True`.
> 3. **Centralized Rate Limiting (Redis):** If scaling the backend to multiple horizontal replicas, migrate in-memory rate limiting to a Redis cluster.
