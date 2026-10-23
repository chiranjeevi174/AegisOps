"""AegisOps — Development Lifecycle Management Script.

Provides consistent, idempotent, and safe lifecycle commands for local development:
  uv run python scripts/dev.py check
  uv run python scripts/dev.py start
  uv run python scripts/dev.py status
  uv run python scripts/dev.py stop [--docker]
  uv run python scripts/dev.py doctor
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = WORKSPACE_ROOT / "logs"
STATE_FILE = LOGS_DIR / "dev_state.json"
DEV_COMPOSE = WORKSPACE_ROOT / "infrastructure" / "compose.yaml"
PROD_COMPOSE = WORKSPACE_ROOT / "infrastructure" / "deployment" / "compose.yaml"
ENV_FILE = WORKSPACE_ROOT / ".env"
INFRA_ENV_FILE = WORKSPACE_ROOT / "infrastructure" / ".env"

DEV_PORTS: dict[str, int] = {
    "fastapi": 8000,
    "simulator": 8001,
    "frontend": 5173,
    "postgres": 5433,
    "prometheus": 9090,
    "grafana": 3000,
    "alertmanager": 9093,
}


def _ensure_dirs() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict[str, Any]:
    _ensure_dirs()
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict[str, Any]) -> None:
    _ensure_dirs()
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _is_port_in_use(port: int, host: str = "localhost") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _http_get(url: str, timeout: float = 5.0) -> tuple[int | None, str]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AegisOps-DevManager"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e)


def _get_process_command_line(pid: int) -> str | None:
    if sys.platform == "win32":
        try:
            cmd = f'Get-CimInstance Win32_Process -Filter "ProcessId = {pid}" | Select-Object -ExpandProperty CommandLine'
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = proc.stdout.strip()
            return out if out else None
        except (subprocess.SubprocessError, OSError):
            return None
    return None


def _find_pid_for_port(port: int) -> int | None:
    if sys.platform == "win32":
        try:
            cmd = f"(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue).OwningProcess"
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = proc.stdout.strip()
            if out:
                first = out.splitlines()[0].strip()
                return int(first)
        except (subprocess.SubprocessError, OSError, ValueError):
            return None
    return None


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return str(pid) in proc.stdout
        except (subprocess.SubprocessError, OSError):
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _safe_terminate_pid(pid: int, expected_keyword: str) -> bool:
    if not _is_pid_alive(pid):
        return False

    cmdline = _get_process_command_line(pid)
    if cmdline and expected_keyword.lower() not in cmdline.lower():
        print(
            f"  [WARN] PID {pid} does not match expected keyword '{expected_keyword}'. Skipping termination for safety."
        )
        return False

    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                capture_output=True,
                timeout=5,
            )
            return True
        except (subprocess.SubprocessError, OSError) as e:
            print(f"  [ERROR] Failed to terminate PID {pid}: {e}")
            return False
    else:
        try:
            os.kill(pid, 15)
            time.sleep(0.5)
            if _is_pid_alive(pid):
                os.kill(pid, 9)
            return True
        except OSError:
            return False


def sync_infra_env() -> None:
    """Ensures infrastructure/.env exists and is populated with required Compose secrets from .env."""
    if not INFRA_ENV_FILE.exists():
        password = "aegisops_local_grafana_dev_secret"
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("GRAFANA_ADMIN_PASSWORD="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val != "change_me":
                        password = val
                    break
        content = (
            "# AegisOps Development Infrastructure Environment\n"
            "# Generated safely by scripts/dev.py — Git ignored\n"
            f"GRAFANA_ADMIN_PASSWORD={password}\n"
        )
        INFRA_ENV_FILE.write_text(content, encoding="utf-8")
        print("  [SYNC] Created infrastructure/.env with development secrets.")


# ==============================================================================
# COMMAND: CHECK
# ==============================================================================
def cmd_check(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("AEGISOPS — PRE-FLIGHT SYSTEM & ENVIRONMENT CHECK")
    print("=" * 60)

    all_ok = True

    # 1. Required Files
    print("\n[1] Checking Required Workspace Files:")
    required_files = [
        ENV_FILE,
        DEV_COMPOSE,
        PROD_COMPOSE,
        WORKSPACE_ROOT / "pyproject.toml",
        WORKSPACE_ROOT / "frontend" / "package.json",
        WORKSPACE_ROOT / "scripts" / "simulate_service.py",
        WORKSPACE_ROOT / "src" / "aegisops" / "main.py",
    ]
    for rf in required_files:
        rel = rf.relative_to(WORKSPACE_ROOT)
        if rf.exists():
            print(f"  [OK] Found {rel}")
        else:
            print(f"  [FAIL] Missing {rel}")
            all_ok = False

    # 2. Infrastructure Env Sync Check
    sync_infra_env()

    # 3. Required CLI Tools
    print("\n[2] Checking Required CLI Tools:")
    tools = ["docker", "uv", "node", "npm"]
    for t in tools:
        found = shutil.which(t)
        if found:
            print(f"  [OK] {t} -> {found}")
        else:
            print(f"  [FAIL] Missing command-line tool: {t}")
            all_ok = False

    # 4. Docker Daemon Status
    print("\n[3] Checking Docker Daemon:")
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            print(f"  [OK] Docker Engine is running (v{proc.stdout.strip()})")
        else:
            print(
                "  [FAIL] Docker Engine responded with error. Ensure Docker Desktop is active."
            )
            all_ok = False
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  [FAIL] Cannot connect to Docker: {e}")
        all_ok = False

    # 5. Port Audit
    print("\n[4] Development Port Status Audit:")
    for name, port in DEV_PORTS.items():
        in_use = _is_port_in_use(port)
        status_text = "Occupied (Listening)" if in_use else "Available"
        print(f"  - Port {port:4d} ({name:12s}): {status_text}")

    print("\n" + "=" * 60)
    if all_ok:
        print("CHECK STATUS: ALL PREREQUISITES SATISFIED")
        return 0
    else:
        print("CHECK STATUS: ISSUES DETECTED (See above failures)")
        return 1


# ==============================================================================
# COMMAND: START
# ==============================================================================
def cmd_start(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("AEGISOPS — IDEMPOTENT DEVELOPMENT STARTUP")
    print("=" * 60)

    _ensure_dirs()
    sync_infra_env()
    state = _load_state()

    # Step 1: Docker Compose Infrastructure
    print("\n[Step 1/5] Verifying Docker Infrastructure:")
    try:
        proc = subprocess.run(
            ["docker", "compose", "-f", str(DEV_COMPOSE), "up", "-d"],
            check=False,
            capture_output=True,
            text=True,
            timeout=40,
        )
        if proc.returncode != 0:
            print(f"  [FAIL] Docker compose up failed:\n{proc.stderr}")
            return 1
        print(
            "  [OK] Docker containers up (PostgreSQL, Prometheus, Grafana, Alertmanager)"
        )
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  [FAIL] Docker execution failed: {e}")
        return 1

    # Wait for PostgreSQL
    print("  Waiting for PostgreSQL readiness...")
    pg_ready = False
    for _ in range(15):
        if _is_port_in_use(DEV_PORTS["postgres"]):
            pg_ready = True
            break
        time.sleep(1)
    if not pg_ready:
        print("  [WARN] PostgreSQL port 5433 did not respond within 15s.")

    # Step 2: Database Migrations
    print("\n[Step 2/5] Running Database Migrations (Alembic):")
    try:
        proc = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=str(WORKSPACE_ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            print("  [OK] Database schema up to date at head.")
        else:
            print(f"  [FAIL] Migration error:\n{proc.stderr}")
            return 1
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  [FAIL] Alembic execution failed: {e}")
        return 1

    # Step 3: Telemetry Simulator
    print("\n[Step 3/5] Telemetry Simulator (Port 8001):")
    code, _ = _http_get("http://127.0.0.1:8001/metrics")
    if code in (200, 307):
        print(
            "  [OK] Telemetry simulator is already healthy and listening. Reusing instance."
        )
        existing_pid = _find_pid_for_port(8001)
        if existing_pid:
            state["simulator"] = {
                "pid": existing_pid,
                "started_at": "discovered_existing",
                "managed": True,
            }
            _save_state(state)
    else:
        print("  Starting Telemetry Simulator in background...")
        with (LOGS_DIR / "simulator.log").open("a", encoding="utf-8") as sim_log:
            kwargs: dict[str, Any] = {
                "cwd": str(WORKSPACE_ROOT),
                "stdout": sim_log,
                "stderr": sim_log,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            proc = subprocess.Popen(
                ["uv", "run", "python", "scripts/simulate_service.py"],
                **kwargs,
            )
        state["simulator"] = {
            "pid": proc.pid,
            "started_at": datetime.now(UTC).isoformat(),
            "managed": True,
        }
        _save_state(state)

        # Wait for simulator to answer
        sim_ok = False
        for _ in range(15):
            code, _ = _http_get("http://127.0.0.1:8001/metrics")
            if code in (200, 307):
                sim_ok = True
                break
            time.sleep(1)
        if sim_ok:
            print(f"  [OK] Telemetry simulator started successfully (PID {proc.pid}).")
        else:
            print(
                "  [WARN] Simulator started but /metrics did not respond within 15s. Check logs/simulator.log."
            )

    # Step 4: FastAPI Backend
    print("\n[Step 4/5] FastAPI Backend (Port 8000):")
    code, body = _http_get("http://127.0.0.1:8000/health/live")
    if code == 200 and "aegisops" in body:
        print(
            "  [OK] FastAPI backend is already running and healthy. Reusing instance (preventing WinError 10013)."
        )
        existing_pid = _find_pid_for_port(8000)
        if existing_pid:
            state["backend"] = {
                "pid": existing_pid,
                "started_at": "discovered_existing",
                "managed": True,
            }
            _save_state(state)
    else:
        print("  Starting FastAPI backend with Uvicorn in background...")
        with (LOGS_DIR / "backend.log").open("a", encoding="utf-8") as api_log:
            kwargs = {"cwd": str(WORKSPACE_ROOT), "stdout": api_log, "stderr": api_log}
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            proc = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "aegisops.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--reload",
                ],
                **kwargs,
            )
        state["backend"] = {
            "pid": proc.pid,
            "started_at": datetime.now(UTC).isoformat(),
            "managed": True,
        }
        _save_state(state)

        # Wait for backend liveness
        api_ok = False
        for _ in range(20):
            code, body = _http_get("http://127.0.0.1:8000/health/live")
            if code == 200 and "aegisops" in body:
                api_ok = True
                break
            time.sleep(1)
        if api_ok:
            print(f"  [OK] FastAPI backend started successfully (PID {proc.pid}).")
        else:
            print(
                "  [WARN] FastAPI started but /health/live did not respond within 20s. Check logs/backend.log."
            )

    # Step 5: Frontend Dev Server
    print("\n[Step 5/5] React Frontend Dev Server (Port 5173):")
    code, _ = _http_get("http://localhost:5173")
    if code == 200:
        print(
            "  [OK] Frontend dev server is already running and responding. Reusing instance."
        )
        existing_pid = _find_pid_for_port(5173)
        if existing_pid:
            state["frontend"] = {
                "pid": existing_pid,
                "started_at": "discovered_existing",
                "managed": True,
            }
            _save_state(state)
    else:
        print("  Starting Frontend development server in background...")
        with (LOGS_DIR / "frontend.log").open("a", encoding="utf-8") as fe_log:
            kwargs = {
                "cwd": str(WORKSPACE_ROOT / "frontend"),
                "stdout": fe_log,
                "stderr": fe_log,
                "shell": True,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            proc = subprocess.Popen(
                "npm run dev",
                **kwargs,
            )
        state["frontend"] = {
            "pid": proc.pid,
            "started_at": datetime.now(UTC).isoformat(),
            "managed": True,
        }
        _save_state(state)

        # Wait for frontend to respond
        fe_ok = False
        for _ in range(20):
            code, _ = _http_get("http://localhost:5173")
            if code == 200:
                fe_ok = True
                break
            time.sleep(1)
        if fe_ok:
            print(f"  [OK] Frontend dev server started successfully (PID {proc.pid}).")
        else:
            print(
                "  [WARN] Frontend started but did not respond within 20s. Check logs/frontend.log."
            )

    print("\n" + "=" * 60)
    print("STARTUP COMPLETE — SERVICE ENDPOINTS:")
    print("  Frontend Operator Dashboard : http://localhost:5173")
    print("  FastAPI Interactive Swagger : http://localhost:8000/docs")
    print("  Prometheus Server UI        : http://localhost:9090")
    print("  Grafana Monitoring UI       : http://localhost:3000")
    print("  Alertmanager UI             : http://localhost:9093")
    print("=" * 60)
    return 0


# ==============================================================================
# COMMAND: STATUS
# ==============================================================================
def cmd_status(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("AEGISOPS — PLATFORM OPERATIONAL STATUS")
    print("=" * 60)

    # 1. Docker Containers
    print("\n[1] Docker Compose Services:")
    try:
        proc = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(DEV_COMPOSE),
                "ps",
                "--format",
                "table {{.Service}}\t{{.State}}\t{{.Health}}\t{{.Ports}}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            print(proc.stdout.strip())
        else:
            print("  [WARN] Failed to query docker compose ps")
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  [ERROR] Docker query error: {e}")

    # 2. Endpoints Health
    print("\n[2] Application & Infrastructure Endpoints:")
    endpoints = [
        ("FastAPI Liveness", "http://127.0.0.1:8000/health/live", 200),
        ("FastAPI Readiness", "http://127.0.0.1:8000/health/ready", 200),
        ("FastAPI Swagger Docs", "http://127.0.0.1:8000/docs", 200),
        ("FastAPI Metrics Scrape", "http://127.0.0.1:8000/metrics", 200),
        ("Simulator Metrics", "http://127.0.0.1:8001/metrics/", 200),
        ("Prometheus Server", "http://localhost:9090/-/healthy", 200),
        ("Alertmanager Server", "http://localhost:9093/-/healthy", 200),
        ("Grafana Web UI", "http://localhost:3000/api/health", 200),
        ("Frontend Web App", "http://localhost:5173", 200),
    ]

    for name, url, expected in endpoints:
        code, _ = _http_get(url)
        if code == expected:
            print(f"  [OK]      {name:25s} -> HTTP {code} ({url})")
        else:
            print(f"  [FAIL]    {name:25s} -> HTTP {code} (Expected {expected})")

    # 3. Prometheus Scrape Targets
    print("\n[3] Prometheus Scrape Targets:")
    code, body = _http_get("http://localhost:9090/api/v1/targets")
    if code == 200:
        try:
            data = json.loads(body)
            targets = data.get("data", {}).get("activeTargets", [])
            for t in targets:
                job = t.get("labels", {}).get("job", "unknown")
                health = t.get("health", "unknown")
                last_err = t.get("lastError", "")
                icon = "[OK]" if health == "up" else "[WARN]"
                err_suffix = f" (Error: {last_err})" if last_err else ""
                print(f"  {icon} Target '{job}': {health.upper()}{err_suffix}")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"  [WARN] Failed to parse Prometheus targets JSON: {e}")
    else:
        print("  [FAIL] Prometheus targets endpoint unreachable")

    # 4. Managed Process State
    state = _load_state()
    print("\n[4] Managed Process Tracker:")
    if state:
        for svc, info in state.items():
            pid = info.get("pid")
            alive = _is_pid_alive(pid) if pid else False
            status_str = f"ALIVE (PID {pid})" if alive else f"STOPPED (Stale PID {pid})"
            print(
                f"  - {svc:12s}: {status_str} (Started: {info.get('started_at', 'unknown')})"
            )
    else:
        print("  No processes actively tracked in logs/dev_state.json")

    print("\n" + "=" * 60)
    return 0


# ==============================================================================
# COMMAND: STOP
# ==============================================================================
def cmd_stop(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("AEGISOPS — SAFE DEVELOPMENT SERVICE SHUTDOWN")
    print("=" * 60)

    state = _load_state()

    # Stop tracked application processes
    process_keywords = {
        "backend": "uvicorn",
        "simulator": "simulate_service",
        "frontend": "vite",
    }

    for svc, kw in process_keywords.items():
        if svc in state and "pid" in state[svc]:
            pid = state[svc]["pid"]
            if _is_pid_alive(pid):
                print(f"Stopping tracked {svc} process (PID {pid})...")
                ok = _safe_terminate_pid(pid, kw)
                if ok:
                    print(f"  [OK] Terminated {svc} (PID {pid}).")
                else:
                    print(f"  [WARN] Could not safely terminate {svc} (PID {pid}).")
            else:
                print(f"Tracked {svc} process (PID {pid}) was already stopped.")
            del state[svc]
        else:
            port = DEV_PORTS.get(svc)
            if port:
                discovered_pid = _find_pid_for_port(port)
                if discovered_pid and _is_pid_alive(discovered_pid):
                    print(
                        f"Stopping active {svc} on port {port} (PID {discovered_pid})..."
                    )
                    ok = _safe_terminate_pid(discovered_pid, kw)
                    if ok:
                        print(f"  [OK] Terminated {svc} (PID {discovered_pid}).")

    _save_state(state)

    # Optional Docker stop
    if getattr(args, "docker", False):
        print(
            "\nStopping Docker infrastructure containers (preserving all volumes and database)..."
        )
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(DEV_COMPOSE), "stop"],
                check=False,
                timeout=30,
            )
            print("  [OK] Docker containers safely stopped.")
        except (subprocess.SubprocessError, OSError) as e:
            print(f"  [ERROR] Failed to stop Docker containers: {e}")
    else:
        print(
            "\nNote: Docker containers remain running. Use 'uv run python scripts/dev.py stop --docker' to stop them."
        )

    print("\n" + "=" * 60)
    print("SHUTDOWN COMPLETE.")
    return 0


# ==============================================================================
# COMMAND: DOCTOR
# ==============================================================================
def cmd_doctor(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("AEGISOPS — SYSTEM & SERVICE DIAGNOSTIC DOCTOR")
    print("=" * 60)

    issues: list[str] = []

    # 1. Environment files check
    print("\n[DIAGNOSTIC 1] Environment Integrity:")
    if not ENV_FILE.exists():
        issues.append("Missing root .env file. Copy from .env.example.")
        print("  [FAIL] Missing .env file.")
    else:
        print("  [PASS] Root .env present.")

    if not INFRA_ENV_FILE.exists():
        issues.append(
            "infrastructure/.env missing. Run 'python scripts/dev.py check' to sync."
        )
        print("  [FAIL] infrastructure/.env missing.")
    else:
        print("  [PASS] infrastructure/.env present.")

    # 2. Port Binding & Conflicts
    print("\n[DIAGNOSTIC 2] Port Bindings:")
    for name, port in DEV_PORTS.items():
        in_use = _is_port_in_use(port)
        if not in_use:
            print(f"  [INFO] Port {port} ({name}) is inactive.")
        else:
            print(f"  [PASS] Port {port} ({name}) is active.")

    # 3. Docker Health Check
    print("\n[DIAGNOSTIC 3] Docker Infrastructure:")
    try:
        proc = subprocess.run(
            ["docker", "compose", "-f", str(DEV_COMPOSE), "ps", "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            lines = [
                json.loads(line)
                for line in proc.stdout.strip().splitlines()
                if line.strip()
            ]
            for c in lines:
                service = c.get("Service", "unknown")
                state = c.get("State", "unknown")
                health = c.get("Health", "")
                health_str = f" ({health})" if health else ""
                print(f"  Container '{service}': {state}{health_str}")
        else:
            issues.append("Docker containers are not running.")
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as e:
        issues.append(f"Docker query failed: {e}")

    # 4. Telemetry Simulator Diagnostic
    print("\n[DIAGNOSTIC 4] Telemetry & Monitoring Pipeline:")
    sim_code, _ = _http_get("http://127.0.0.1:8001/metrics")
    if sim_code not in (200, 307):
        issues.append(
            "Telemetry simulator is not responding on http://127.0.0.1:8001. Start with 'python scripts/dev.py start'."
        )
        print("  [FAIL] Telemetry simulator unreachable on port 8001.")
    else:
        print("  [PASS] Telemetry simulator /metrics responds OK.")

    prom_code, _ = _http_get("http://localhost:9090/-/healthy")
    if prom_code != 200:
        issues.append("Prometheus server is unreachable on http://localhost:9090.")
        print("  [FAIL] Prometheus unreachable.")
    else:
        print("  [PASS] Prometheus server healthy.")

    # Query telemetry from Prometheus
    t_code, t_body = _http_get(
        "http://localhost:9090/api/v1/query?query=aegisops_sim_service_up"
    )
    if t_code == 200 and "result" in t_body:
        with suppress(json.JSONDecodeError, KeyError, IndexError):
            data = json.loads(t_body)
            results = data.get("data", {}).get("result", [])
            if results:
                val = results[0].get("value", [None, None])[1]
                print(
                    f"  [PASS] Prometheus successfully evaluates 'aegisops_sim_service_up' -> {val}"
                )
            else:
                issues.append(
                    "Prometheus has no samples for 'aegisops_sim_service_up'. Ensure simulator has run for >= 15 seconds."
                )
                print("  [WARN] No samples for 'aegisops_sim_service_up' yet.")

    # 5. FastAPI Backend Diagnostics
    print("\n[DIAGNOSTIC 5] FastAPI Backend Dependencies:")
    ready_code, ready_body = _http_get("http://127.0.0.1:8000/health/ready")
    if ready_code == 200:
        with suppress(json.JSONDecodeError, KeyError):
            data = json.loads(ready_body)
            deps = data.get("dependencies", {})
            for d_name, d_info in deps.items():
                d_stat = d_info.get("status", "unknown")
                d_lat = d_info.get("latency_ms")
                lat_str = f" ({d_lat:.2f}ms)" if d_lat is not None else ""
                icon = "[PASS]" if d_stat in ("up", "configured") else "[FAIL]"
                print(f"  {icon} Dependency '{d_name}': {d_stat}{lat_str}")
        print("  [PASS] Backend readiness endpoint responds OK.")
    else:
        issues.append(
            "FastAPI backend is unreachable or not ready on http://127.0.0.1:8000."
        )
        print(f"  [FAIL] Backend /health/ready returned HTTP {ready_code}")

    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY:")
    if not issues:
        print(
            "  HEALTHY: No active issues detected. All platform services are operational."
        )
        return 0
    else:
        print(f"  {len(issues)} ISSUE(S) FOUND:")
        for idx, iss in enumerate(issues, 1):
            print(f"  {idx}. {iss}")
        return 1


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================
def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="AegisOps Development Lifecycle Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    subparsers.add_parser(
        "check", help="Verify workspace files, tools, and environment prerequisites"
    )

    # start
    subparsers.add_parser(
        "start", help="Idempotently start development infrastructure and applications"
    )

    # status
    subparsers.add_parser(
        "status",
        help="Query and display the operational status of all platform services",
    )

    # stop
    stop_parser = subparsers.add_parser(
        "stop", help="Safely stop development processes"
    )
    stop_parser.add_argument(
        "--docker",
        action="store_true",
        help="Also stop Docker containers without deleting volumes or data",
    )

    # doctor
    subparsers.add_parser("doctor", help="Run deep system and service diagnostics")

    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "start": cmd_start,
        "status": cmd_status,
        "stop": cmd_stop,
        "doctor": cmd_doctor,
    }

    handler = commands.get(args.command)
    if handler:
        sys.exit(handler(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
