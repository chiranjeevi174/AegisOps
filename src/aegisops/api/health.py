import asyncio
from datetime import UTC, datetime
from typing import Annotated

import requests
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.core.config import get_settings
from aegisops.db.session import get_db

router = APIRouter(tags=["System & Health"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


class ComponentHealth(BaseModel):
    status: str
    critical: bool
    latency_ms: float | None = None
    details: str | None = None


class ReadinessResponse(BaseModel):
    status: str  # "ready", "degraded", "not_ready"
    timestamp: str
    service: str
    dependencies: dict[str, ComponentHealth]


@router.get("/health")
@router.get("/health/live")
def health_liveness():
    """Liveness probe: verifies that the FastAPI process is running and responsive."""
    return {
        "status": "healthy",
        "service": "aegisops",
    }


@router.get("/health/ready", response_model=ReadinessResponse)
async def health_readiness(
    db: DbSession,
    response: Response,
):
    """Readiness probe: validates critical dependencies with bounded timeouts."""
    settings = get_settings()
    deps: dict[str, ComponentHealth] = {}
    is_ready = True

    # 1. PostgreSQL (Critical)
    db_start = datetime.now(UTC)
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2.0)
        db_latency = (datetime.now(UTC) - db_start).total_seconds() * 1000.0
        deps["database"] = ComponentHealth(
            status="up",
            critical=True,
            latency_ms=round(db_latency, 2),
            details="PostgreSQL query succeeded",
        )
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        is_ready = False
        deps["database"] = ComponentHealth(
            status="down",
            critical=True,
            details=f"Database check failed: {type(exc).__name__}",
        )

    # 2. Prometheus (Non-critical telemetry dependency)
    prom_start = datetime.now(UTC)
    try:
        prom_resp = await asyncio.to_thread(
            requests.get,
            f"{settings.prometheus_url.rstrip('/')}/-/healthy",
            timeout=2.0,
        )
        prom_latency = (datetime.now(UTC) - prom_start).total_seconds() * 1000.0
        if prom_resp.status_code == 200:
            deps["prometheus"] = ComponentHealth(
                status="up",
                critical=False,
                latency_ms=round(prom_latency, 2),
                details="Prometheus endpoint healthy",
            )
        else:
            deps["prometheus"] = ComponentHealth(
                status="degraded",
                critical=False,
                details=f"Prometheus returned HTTP {prom_resp.status_code}",
            )
    except (requests.RequestException, OSError, TimeoutError) as exc:
        deps["prometheus"] = ComponentHealth(
            status="degraded",
            critical=False,
            details=f"Prometheus unreachable: {type(exc).__name__}",
        )

    # 3. Gemini Configuration (Non-critical, local config check only - no paid API calls)
    has_gemini_key = bool(settings.gemini_api_key.get_secret_value().strip())
    deps["gemini_config"] = ComponentHealth(
        status="configured" if has_gemini_key else "not_configured",
        critical=False,
        details=f"Model: {settings.gemini_model}",
    )

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "not_ready"
    elif any(d.status in ("degraded", "not_configured") for d in deps.values()):
        overall_status = "degraded"
    else:
        overall_status = "ready"

    return ReadinessResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        service="aegisops",
        dependencies=deps,
    )
