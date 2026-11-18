# AegisOps — Windows CMD Execution Handbook

**Agentic SRE & Autonomous Incident Response Platform**  
*Beginner-Friendly Command-Line Guide for Local Development, Testing, and Demonstration*

---

## 1. Quick Start Overview

To run and demonstrate the complete AegisOps platform on Windows, you will open **5 command prompt (CMD) windows**, each dedicated to a clean, isolated service component:

```
[Window 1] Docker Infrastructure (PostgreSQL 16, Prometheus, Grafana)
[Window 2] Telemetry Simulator & Control Server (Port 8001)
[Window 3] FastAPI Backend & Agentic AI Engine (Port 8000)
[Window 4] React 18 SRE Command Center Frontend (Port 5173)
[Window 5] SRE Operator CLI & Automated Verification Suite
```

> [!NOTE]
> All commands assume your working directory is the project root:
> `D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps`

---

## 2. Step-by-Step Terminal Commands

### Terminal 1 — Infrastructure Containers (PostgreSQL, Prometheus, Grafana)

Open CMD Window 1 and run:

```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps"

:: Start Docker Compose services in detached mode
docker compose -f infrastructure/compose.yaml up -d

:: Verify container health and port bindings
docker compose -f infrastructure/compose.yaml ps
```

**Expected Output:**
- `aegisops-postgres`: Up (healthy) on port `5433` (or `5432`).
- `aegisops-prometheus`: Up on port `9090`.
- `aegisops-alertmanager`: Up on port `9093`.
- `aegisops-grafana`: Up on port `3000`.

---

### Terminal 2 — Database Migrations & Telemetry Simulator

Open CMD Window 2 and run:

```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps"

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Verify database migrations are at head
python -m alembic upgrade head

:: Start the Telemetry Simulator on port 8001
python scripts/simulate_service.py
```

**Expected Output:**
```text
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

---

### Terminal 3 — FastAPI Backend & LangGraph Agentic Engine

Open CMD Window 3 and run:

```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps"

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Set Python Path to src/
set PYTHONPATH=src

:: Start the FastAPI backend on port 8000
python -m uvicorn aegisops.main:app --host 127.0.0.1 --port 8000 --reload
```

**Expected Output:**
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

### Terminal 4 — React 18 SRE Command Center Frontend

Open CMD Window 4 and run:

```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps\frontend"

:: Start the Vite development server on port 5173
npm run dev
```

**Expected Output:**
```text
  VITE v6.4.4  ready in 450 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Now open your web browser and navigate to: **`http://localhost:5173`**

---

### Terminal 5 — Automated End-to-End Verification & Operator Actions

Open CMD Window 5 for interactive commands, scenario triggering, and testing.

#### 1. Run the Full Automated End-to-End Verification Test
This automated test executes all 14 stages of incident response, AI investigation, separation-of-duties enforcement, demo remediation, telemetry verification, and stateful rollback:

```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps"
call .venv\Scripts\activate.bat
set PYTHONPATH=src

python scripts/verify_demo_execution_e2e.py
```

**Expected Output:**
```text
================================================================================
 ALL 14 END-TO-END DEMO EXECUTION & ROLLBACK STAGES PASSED SUCCESSFULLY!
================================================================================
```

> **Key Operational Disclosures:**
> - **Verification Outcome Truthfulness (Stage 10):** Post-execution verification against Prometheus is truthfully reported as `inconclusive`. Because the script triggers verification immediately (~2 seconds post-remediation), the sampling window lacks sufficient observation time for statistical certainty. The platform deliberately refuses to declare false-positive success.
> - **Demo Rollback Scope (Stages 12–13):** Demo rollback exclusively reverts the local telemetry simulator (`http://127.0.0.1:8001`) from `healthy` back to `high_cpu`. It does **not** alter live production infrastructure or cloud deployments.

---

## 3. Simulator Scenario Control Commands

You can interactively change the telemetry scenario on the simulator from Terminal 5 using `curl`:

### Trigger High CPU Degradation
Forces CPU to 95%, p99 latency to 2.4s, and fires Prometheus alert rules:
```cmd
curl -X POST http://127.0.0.1:8001/control/scenario/high_cpu
```

### Trigger Memory Leak
Forces memory to 98% and increases latency to 4.2s:
```cmd
curl -X POST http://127.0.0.1:8001/control/scenario/memory_leak
```

### Trigger Downstream Dependency Failure
Forces HTTP 5xx error rate to 42%:
```cmd
curl -X POST http://127.0.0.1:8001/control/scenario/downstream_failure
```

### Trigger Complete Service Outage
Takes the microservice offline (`service_up = 0`):
```cmd
curl -X POST http://127.0.0.1:8001/control/scenario/service_outage
```

### Restore Healthy Telemetry Baseline
Resets CPU to 25%, latency to 80ms, error rate to 0.1%:
```cmd
curl -X POST http://127.0.0.1:8001/control/scenario/healthy
```

### Inspect Current Telemetry State
```cmd
curl http://127.0.0.1:8001/control/state
```

---

## 4. Persona Authentication & Token Generation

To test backend APIs directly from Windows CMD with role-based JWT tokens, use the following commands:

### Generate Operator Token (`sre-operator-dan`)
```cmd
curl -X POST http://127.0.0.1:8000/api/v1/auth/switch-persona/sre-operator-dan
```

### Generate Lead Approver Token (`sre-lead-rachel`)
```cmd
curl -X POST http://127.0.0.1:8000/api/v1/auth/switch-persona/sre-lead-rachel
```

### Check Current Authenticated Identity
Replace `<TOKEN>` with the token string returned from the switch-persona endpoint:
```cmd
curl -H "Authorization: Bearer <TOKEN>" http://127.0.0.1:8000/api/v1/auth/me
```

---

## 5. Running Test Suites

### Backend Pytest Suite (245+ Tests)
```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps"
call .venv\Scripts\activate.bat
set PYTHONPATH=src

:: Run execution and rollback test suite
python -m pytest tests/test_rollbacks.py tests/test_executions.py tests/test_verifications.py -v

:: Run complete platform pytest suite
python -m pytest
```

### Frontend Vitest Suite & Production Build
```cmd
cd /d "D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps\frontend"

:: Run all Vitest unit and integration tests
npm run test

:: Run TypeScript compile and Vite production build
npm run build
```

---

## 6. Graceful System Shutdown

When you have finished testing:

1. In **Terminal 4** (Frontend): Press `Ctrl + C`
2. In **Terminal 3** (Backend): Press `Ctrl + C`
3. In **Terminal 2** (Simulator): Press `Ctrl + C`
4. In **Terminal 1** (Infrastructure): Run:
   ```cmd
   docker compose -f infrastructure/compose.yaml down
   ```
   *(This preserves your PostgreSQL database volume and container configuration).*
