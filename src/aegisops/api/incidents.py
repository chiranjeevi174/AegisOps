from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.schemas import IncidentCreate, IncidentResponse
from aegisops.core.auth import (
    AuthenticatedActor,
    get_incident_analyzer_actor,
)
from aegisops.core.rate_limit import rate_limit_analysis
from aegisops.db.session import get_db
from aegisops.services import incidents
from aegisops.services.incidents import IncidentNotFoundError, run_incident_workflow

router = APIRouter(prefix="/incidents", tags=["Incidents"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


class IncidentAnalysisResponse(BaseModel):
    incident_id: UUID
    title: str
    severity: str
    priority: str | None = None
    requires_escalation: bool | None = None
    evidence: dict[str, Any] | None = None
    evidence_collected_at: str | None = None
    investigation: dict[str, Any] | None = None
    historical_evidence: dict[str, Any] | None = None
    rca: dict[str, Any] | None = None
    remediation_plan: dict[str, Any] | None = None
    errors: dict[str, str | None] = {}


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    data: IncidentCreate,
    db: DbSession,
):
    return await incidents.create_incident(db, data)


@router.get("", response_model=list[IncidentResponse])
async def list_incidents(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await incidents.list_incidents(db, limit, offset)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    db: DbSession,
):
    incident = await incidents.get_incident(db, incident_id)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident


@router.post(
    "/{incident_id}/analyze",
    response_model=IncidentAnalysisResponse,
    dependencies=[Depends(rate_limit_analysis)],
)
async def analyze_incident(
    incident_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_incident_analyzer_actor)],
    db: DbSession,
):
    """Executes the agentic investigation, RCA, and remediation planning workflow on demand."""
    try:
        result = await run_incident_workflow(db, incident_id)
        errors = {}
        for err_key in [
            "monitoring_error",
            "investigation_error",
            "historical_evidence_error",
            "rca_error",
            "remediation_error",
        ]:
            if result.get(err_key):
                errors[err_key] = result.get(err_key)

        return IncidentAnalysisResponse(
            incident_id=result["incident_id"],
            title=result["title"],
            severity=result["severity"],
            priority=result.get("priority"),
            requires_escalation=result.get("requires_escalation"),
            evidence=result.get("evidence"),
            evidence_collected_at=result.get("evidence_collected_at"),
            investigation=result.get("investigation"),
            historical_evidence=result.get("historical_evidence"),
            rca=result.get("rca"),
            remediation_plan=result.get("remediation_plan"),
            errors=errors,
        )
    except IncidentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation workflow failed: {exc}",
        )
