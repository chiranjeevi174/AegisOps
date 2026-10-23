# AegisOps Frontend Operator Dashboard

Enterprise SRE and Autonomous Incident Response Platform Operator Dashboard built with React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, and React Router.

---

## 1. Frontend Technology Stack

| Layer | Technology |
|---|---|
| Framework | React 18 (`react`, `react-dom`) |
| Language | TypeScript (Strict mode enabled) |
| Build Tool | Vite 6 |
| Styling | Tailwind CSS 3 (Dark-first enterprise theme) |
| Routing | React Router v6 |
| Server State | TanStack Query v5 (`@tanstack/react-query`) |
| HTTP Client | Axios with centralized error mapping and session cookies |
| Forms | React Hook Form + Zod schema validation |
| Icons | Lucide React |
| Telemetry Visuals | Recharts |
| Testing | Vitest + React Testing Library + jsdom |

---

## 2. Directory Structure

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── App.tsx             # Root application shell & auth initialization
│   │   ├── router.tsx          # Client-side route declarations
│   │   └── providers.tsx       # QueryClient, Auth, and Router providers
│   │
│   ├── components/
│   │   ├── feedback/           # Skeleton, EmptyState, AlertMessage
│   │   ├── layout/             # Sidebar, Header, AppLayout, PersonaSwitcher
│   │   └── ui/                 # Badge, Button, Card, Modal, Input, SafetyBanner
│   │
│   ├── features/
│   │   ├── approvals/          # Plan review, approval, revision, rejection
│   │   ├── audit/              # Unified audit event stream & inspection
│   │   ├── dashboard/          # Metrics overview, severity breakdown, telemetry
│   │   ├── executions/         # Safe simulation & restricted live diagnostics
│   │   ├── incidents/          # Incident inventory & comprehensive detail view
│   │   ├── investigation/      # Gemini investigation & evidence-backed RCA
│   │   ├── remediation/        # Safe remediation planning with safety bounds
│   │   ├── rollbacks/          # Post-execution rollback readiness assessments
│   │   ├── settings/           # Non-sensitive runtime configs & health status
│   │   └── verifications/      # Post-execution verification & metric deltas
│   │
│   ├── services/
│   │   └── api.ts              # Centralized Axios client & typed endpoints
│   │
│   ├── test/                   # Vitest unit & integration test suites
│   ├── types/                  # Strict TypeScript domain interfaces
│   ├── styles/                 # Tailwind design tokens & dark-first CSS
│   └── main.tsx                # Application bootstrap
│
├── .env.example
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 3. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Default variables (`.env.example`):
```env
VITE_API_BASE_URL=/api/v1
VITE_GRAFANA_URL=http://localhost:3000
```

> **Security Note**: No secret keys, passwords, or bearer tokens are placed in `.env` or Vite bundles. Authentication is backend-mediated via development session cookies.

---

## 4. Local Development Startup Instructions (Windows CMD)

### Step 1: Start Supporting Infrastructure (PostgreSQL, Prometheus, Grafana, Alertmanager)
```cmd
docker compose up -d
```

### Step 2: Run Database Migrations
```cmd
uv run alembic upgrade head
```

### Step 3: Start the FastAPI Backend Server
```cmd
uv run uvicorn aegisops.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: (Optional) Run Synthetic Target Service & Simulator
```cmd
uv run python scripts/run_simulator.py
```

### Step 5: Start Frontend Development Server
```cmd
cd frontend
npm install
npm run dev
```

The frontend dashboard will be accessible at:
```text
http://localhost:5173
```
All `/api/*` network requests are automatically proxied to `http://localhost:8000` via Vite.

---

## 5. Available Pages & Capabilities

1. **Overview (`/`)**:
   - System metrics (Total incidents, Active alerts, Pending approvals, Completed diagnostics, Rollback readiness).
   - Prometheus target availability trends.
   - Severity distribution breakdown.
   - Quick launch to Grafana dashboards.

2. **Incidents (`/incidents`)**:
   - Filterable, searchable table of alerts and incidents.
   - Status, severity, and source filters.
   - Manual incident creation dialog for testing triage workflows.

3. **Incident Detail (`/incidents/:id`)**:
   - Comprehensive multi-tab incident command view.
   - Tabbed access to Evidence, Gemini Investigation, RCA Hypotheses, Remediation Plans, Approvals, Executions, Verifications, and Rollbacks.
   - Operator-initiated LangGraph analysis trigger (`POST /incidents/{id}/analyze`).

4. **Investigations & RCA (`/investigations`)**:
   - Raw Prometheus observations vs Gemini-generated hypotheses.
   - Evidence categorization (Supporting, Contradicting, Missing).
   - Root cause confirmation guardrails (`Root Cause Confirmed: False`).

5. **Remediation Plans (`/remediation`)**:
   - Validated safety bounds: `Execution Enabled: False`, `Human Approval Required: True`.
   - Inspection of prerequisites, validation steps, and rollback considerations.
   - Approval request initiation for validated plans.

6. **Approvals (`/approvals`)**:
   - Lifecycle filtering: Pending, Approved, Rejected, Revision Requested, Expired, Superseded.
   - Exact immutable plan snapshot and hash inspection.
   - Decision dialogs with mandatory rejection reasons and self-approval restrictions.

7. **Executions (`/executions`)**:
   - Server-defined operation registry (e.g. `test_connectivity_diagnostic`, `collect_thread_dump`).
   - Dry-run simulation execution (`POST /api/v1/executions/simulate`).
   - Restricted live diagnostic execution (`POST /api/v1/executions/diagnose`) with explicit confirmation.
   - No arbitrary shell commands allowed.

8. **Post-Execution Verifications (`/verifications`)**:
   - Baseline vs follow-up metric sampling.
   - Directional change and statistical deltas.
   - Truthful outcome classification (`DIAGNOSTIC_VERIFIED`, `INCONCLUSIVE`, `FAILED`).
   - Remediation success confirmation guardrails.

9. **Rollback Readiness (`/rollbacks`)**:
   - Pre-flight rollback readiness checklist and risk classification.
   - Simulation-only result rendering.
   - Truthful non-applicable state for read-only diagnostics (`Rollback: Not Applicable`).
   - Invariant display: `Rollback Execution Enabled: False`, `System Changes Performed: False`.

10. **Audit History (`/audit`)**:
    - Centralized read-only event stream (Approvals, Executions, Verifications, Rollbacks).
    - Actor attribution and sanitized payload inspection.

11. **Settings (`/settings`)**:
    - Backend connectivity and version check.
    - Prometheus and Grafana integration health.
    - RBAC Actor permissions matrix (Viewer, SRE Lead, Operator, DevOps Engineer).

---

## 6. Authentication and Authorization Model

- **Session Handling**: Utilizes development-grade backend sessions via secure `aegisops_session` HttpOnly cookies or Authorization Bearer tokens.
- **Actor Switching**: Provides a top-bar persona switcher to test role-based access controls across `lead_sre`, `ops_engineer`, `devops_eng`, and `observer`.
- **Zero Secrets**: No tokens or passwords exist in frontend code or bundle assets.
- **Client Guardrails**: Action buttons (e.g. Approve, Simulate, Diagnose) reflect backend permissions, while backend enforces authorization independently.

---

## 7. Verification and Testing Commands

Run all verification scripts from the `frontend/` directory:

```cmd
cd frontend
```

### Run Linter
```cmd
npm run lint
```

### Run TypeScript Type Check
```cmd
npm run typecheck
```

### Run Unit and Integration Test Suite
```cmd
npm run test
```

### Build Production Bundle
```cmd
npm run build
```

---

## 8. Known Limitations & Safety Boundaries

- **Zero Autonomous Mutation**: The frontend adheres strictly to AegisOps safety principles. No buttons or forms exist for real infrastructure modification, SSH commands, or Kubernetes mutations.
- **Operator-Driven AI Analysis**: Gemini investigations are only triggered upon explicit operator action, preventing runaway API calls on page reloads.
- **Rollback Safety**: Rollback assessments are strictly simulation-based. No live rollback execution endpoints exist.
