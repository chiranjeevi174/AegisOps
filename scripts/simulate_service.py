import asyncio
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI
from prometheus_client import Gauge, make_asgi_app

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


def apply_scenario(name: str) -> None:
    cpu, latency, error_rate, service_up = SCENARIOS[name]

    CPU.set(cpu)
    LATENCY.set(latency)
    ERROR_RATE.set(error_rate)
    SERVICE_UP.set(service_up)

    for scenario in SCENARIOS:
        SCENARIO.labels(name=scenario).set(int(scenario == name))

    print(f"Active simulation: {name}", flush=True)


async def run_simulation() -> None:
    while True:
        for name in SCENARIOS:
            apply_scenario(name)
            await asyncio.sleep(45)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_simulation())

    try:
        yield
    finally:
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="AegisOps Service Simulator",
    lifespan=lifespan,
)

app.mount("/metrics", make_asgi_app())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
