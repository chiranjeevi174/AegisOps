import asyncio
import logging
from datetime import UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.schemas import IncidentCreate
from aegisops.domain.incident import Incident
from aegisops.observability.metrics import INCIDENTS_CREATED, WORKFLOW_RUNS
from aegisops.workflows.incident import incident_workflow
from aegisops.workflows.state import IncidentState

logger = logging.getLogger(__name__)


class IncidentNotFoundError(Exception):
    """Raised when an incident does not exist in the database."""


async def create_incident(
    session: AsyncSession,
    data: IncidentCreate,
) -> Incident:
    incident = Incident(**data.model_dump())

    session.add(incident)

    await session.commit()
    await session.refresh(incident)
    INCIDENTS_CREATED.labels(severity=incident.severity).inc()

    return incident


async def get_incident(
    session: AsyncSession,
    incident_id: UUID,
) -> Incident | None:
    return await session.get(Incident, incident_id)


async def list_incidents(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[Incident]:
    result = await session.scalars(
        select(Incident)
        .order_by(Incident.created_at.desc(), Incident.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(result.all())


async def run_incident_workflow(
    session: AsyncSession,
    incident_id: UUID,
) -> dict:
    incident = await get_incident(session, incident_id)
    if incident is None:
        raise IncidentNotFoundError(f"Incident {incident_id} not found")

    alert_name = None
    if incident.source == "alertmanager" or incident.alert_fingerprint:
        if "cpu" in incident.title.lower():
            alert_name = "HighCPUUsage"
        else:
            alert_name = incident.title
    elif incident.title:
        alert_name = (
            "HighCPUUsage" if "cpu" in incident.title.lower() else incident.title
        )

    state: IncidentState = {
        "incident_id": incident.id,
        "title": incident.title,
        "severity": incident.severity,  # type: ignore[typeddict-item]
        "status": incident.status,
    }

    if alert_name:
        state["alert_name"] = alert_name

    started_at = incident.alert_started_at or incident.created_at
    if started_at:
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        else:
            started_at = started_at.astimezone(UTC)
        state["alert_started_at"] = started_at.isoformat()

    logger.info(
        "Incident workflow run started",
        extra={"event": "workflow_start", "incident_id": str(incident.id)},
    )
    try:
        result = await asyncio.to_thread(incident_workflow.invoke, state)
        WORKFLOW_RUNS.labels(status="succeeded").inc()
        logger.info(
            "Incident workflow run completed",
            extra={
                "event": "workflow_complete",
                "incident_id": str(incident.id),
            },
        )
        return result
    except Exception as exc:
        WORKFLOW_RUNS.labels(status="failed").inc()
        logger.exception(
            "Incident workflow run failed",
            extra={
                "event": "workflow_failure",
                "incident_id": str(incident.id),
                "error_category": type(exc).__name__,
            },
        )
        raise
