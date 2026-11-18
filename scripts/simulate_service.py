import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from prometheus_client import Gauge, make_asgi_app
from pydantic import BaseModel, Field

CPU = Gauge(
    "aegisops_sim_cpu_usage_percent",
    "Simulated CPU utilization",
)

LATENCY = Gauge(
    "aegisops_sim_latency_seconds",
    "Simulated API response latency",
)

ERROR_RATE = Gauge(
    "aegisops_sim_error_rate",
    "Simulated HTTP error ratio",
)

SERVICE_UP = Gauge(
    "aegisops_sim_service_up",
    "Simulated service availability",
)

SCENARIO = Gauge(
    "aegisops_sim_scenario",
    "Currently active simulation scenario",
    ["name"],
)


SCENARIOS = {
    "healthy": (25, 0.08, 0.001, 1),
    "high_cpu": (94, 0.25, 0.01, 1),
    "high_latency": (45, 2.8, 0.02, 1),
    "error_spike": (55, 0.5, 0.35, 1),
    "service_degradation": (85, 4.2, 0.65, 0),
}

# State management for demo control
_state = {
    "active_scenario": "healthy",
    "auto_cycle": True,
    "last_scenario_change": datetime.now(UTC).isoformat(),
    "rollback_snapshot": None,
    "remediation_history": [],
}


def apply_scenario(name: str) -> None:
    if name not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{name}'. Must be one of {list(SCENARIOS.keys())}"
        )

    cpu, latency, error_rate, service_up = SCENARIOS[name]

    CPU.set(cpu)
    LATENCY.set(latency)
    ERROR_RATE.set(error_rate)
    SERVICE_UP.set(service_up)

    for scenario in SCENARIOS:
        SCENARIO.labels(name=scenario).set(int(scenario == name))

    _state["active_scenario"] = name
    _state["last_scenario_change"] = datetime.now(UTC).isoformat()
    print(
        f"Active simulation: {name} (CPU: {cpu}%, Latency: {latency}s, ErrorRate: {error_rate}, Up: {service_up})",
        flush=True,
    )


async def run_simulation() -> None:
    while True:
        if _state["auto_cycle"]:
            for name in SCENARIOS:
                if not _state["auto_cycle"]:
                    break
                apply_scenario(name)
                await asyncio.sleep(45)
        else:
            await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize gauges to healthy baseline
    apply_scenario("healthy")
    task = asyncio.create_task(run_simulation())

    try:
        yield
    finally:
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="AegisOps Service Simulator & Demo Infrastructure",
    description="Simulates microservice metrics and exposes deterministic REST control endpoints for demo remediation and rollback.",
    lifespan=lifespan,
)

app.mount("/metrics", make_asgi_app())


class RemediateRequest(BaseModel):
    action: str = Field(
        default="remediate_service_degradation",
        description="Allowlisted remediation action",
    )
    service_name: str = Field(default="api-service", description="Target service")
    target_scenario: str = Field(
        default="healthy", description="Target healthy scenario"
    )
    incident_id: str | None = Field(
        default=None, description="Associated incident UUID"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Validated operation parameters"
    )


class AutoCycleRequest(BaseModel):
    enabled: bool = Field(
        description="Enable or disable automated periodic scenario cycling"
    )


class ScenarioRequest(BaseModel):
    scenario: str = Field(description="Scenario name to activate")


@app.get("/health")
async def health_check():
    active = _state["active_scenario"]
    cpu, latency, error_rate, up = SCENARIOS[active]
    return {
        "status": "healthy" if up == 1 else "degraded",
        "service": "aegisops-simulator",
        "active_scenario": active,
        "service_up": bool(up),
        "auto_cycle": _state["auto_cycle"],
        "metrics": {
            "cpu_percent": cpu,
            "latency_seconds": latency,
            "error_rate": error_rate,
            "service_up": up,
        },
    }


@app.get("/control/state")
async def get_control_state():
    active = _state["active_scenario"]
    cpu, latency, error_rate, up = SCENARIOS[active]
    return {
        "active_scenario": active,
        "auto_cycle": _state["auto_cycle"],
        "last_scenario_change": _state["last_scenario_change"],
        "has_rollback_snapshot": _state["rollback_snapshot"] is not None,
        "rollback_snapshot": _state["rollback_snapshot"],
        "metrics": {
            "cpu_percent": cpu,
            "latency_seconds": latency,
            "error_rate": error_rate,
            "service_up": up,
        },
        "available_scenarios": list(SCENARIOS.keys()),
        "remediation_history_count": len(_state["remediation_history"]),
    }


@app.post("/control/scenario/{name}")
async def set_scenario(name: str):
    if name not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario '{name}'. Valid scenarios: {list(SCENARIOS.keys())}",
        )
    # Pause auto-cycling so manual scenario stays stable for demonstration
    _state["auto_cycle"] = False
    apply_scenario(name)
    cpu, latency, error_rate, up = SCENARIOS[name]
    return {
        "status": "success",
        "active_scenario": name,
        "auto_cycle": False,
        "metrics": {
            "cpu_percent": cpu,
            "latency_seconds": latency,
            "error_rate": error_rate,
            "service_up": up,
        },
    }


@app.post("/control/auto_cycle")
async def toggle_auto_cycle(payload: AutoCycleRequest):
    _state["auto_cycle"] = payload.enabled
    return {
        "status": "success",
        "auto_cycle": _state["auto_cycle"],
        "active_scenario": _state["active_scenario"],
    }


@app.post("/control/remediate")
async def execute_remediation(payload: RemediateRequest):
    prior_scenario = _state["active_scenario"]
    prior_cpu, prior_latency, prior_err, prior_up = SCENARIOS[prior_scenario]

    # Save state snapshot for reversible rollback
    snapshot = {
        "scenario": prior_scenario,
        "cpu_percent": prior_cpu,
        "latency_seconds": prior_latency,
        "error_rate": prior_err,
        "service_up": prior_up,
        "remediated_at": datetime.now(UTC).isoformat(),
        "action": payload.action,
        "service_name": payload.service_name,
    }
    _state["rollback_snapshot"] = snapshot

    # Pause auto-cycling so remediation stays healthy
    _state["auto_cycle"] = False

    # Apply healthy scenario
    target = (
        payload.target_scenario if payload.target_scenario in SCENARIOS else "healthy"
    )
    apply_scenario(target)
    new_cpu, new_latency, new_err, new_up = SCENARIOS[target]

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": payload.action,
        "service_name": payload.service_name,
        "prior_scenario": prior_scenario,
        "remediated_scenario": target,
        "incident_id": payload.incident_id,
    }
    _state["remediation_history"].append(record)

    return {
        "status": "success",
        "message": f"Remediation '{payload.action}' executed successfully on simulated service '{payload.service_name}'",
        "action": payload.action,
        "previous_state": snapshot,
        "current_state": {
            "scenario": target,
            "cpu_percent": new_cpu,
            "latency_seconds": new_latency,
            "error_rate": new_err,
            "service_up": new_up,
        },
    }


@app.post("/control/rollback")
async def execute_rollback():
    snapshot = _state["rollback_snapshot"]
    target_scenario = snapshot["scenario"] if snapshot else "service_degradation"

    # Pause auto-cycling during rollback
    _state["auto_cycle"] = False
    apply_scenario(target_scenario)
    cpu, latency, error_rate, up = SCENARIOS[target_scenario]

    # Clear snapshot after successful restoration
    _state["rollback_snapshot"] = None

    return {
        "status": "success",
        "message": f"Rollback executed successfully. Restored simulated service to '{target_scenario}' scenario",
        "restored_scenario": target_scenario,
        "current_state": {
            "scenario": target_scenario,
            "cpu_percent": cpu,
            "latency_seconds": latency,
            "error_rate": error_rate,
            "service_up": up,
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
