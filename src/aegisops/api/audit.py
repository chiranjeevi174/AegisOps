from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.core.auth import AuthenticatedActor, get_current_actor
from aegisops.db.session import get_db
from aegisops.domain.approval_event import ApprovalEvent
from aegisops.domain.execution_event import ExecutionEvent
from aegisops.domain.rollback_event import RollbackEvent
from aegisops.domain.verification_event import VerificationEvent

router = APIRouter(prefix="/audit", tags=["Unified Audit History"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


class UnifiedAuditEventResponse(BaseModel):
    id: UUID
    category: Literal["approval", "execution", "verification", "rollback"]
    event_type: str
    resource_id: UUID
    incident_id: UUID | None = None
    actor: str
    previous_status: str | None = None
    new_status: str | None = None
    details: dict[str, Any]
    created_at: datetime


@router.get("/events", response_model=list[UnifiedAuditEventResponse])
async def list_unified_audit_events(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
    category: Literal[
        "all", "approval", "execution", "verification", "rollback"
    ] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Retrieves unified immutable audit trail events across all platform actions."""
    events: list[UnifiedAuditEventResponse] = []

    # Approvals
    if category in ("all", "approval"):
        res = await db.execute(
            select(ApprovalEvent)
            .order_by(desc(ApprovalEvent.created_at))
            .limit(limit + offset)
        )
        for ev in res.scalars().all():
            events.append(
                UnifiedAuditEventResponse(
                    id=ev.id,
                    category="approval",
                    event_type=ev.event_type,
                    resource_id=ev.approval_id,
                    incident_id=ev.incident_id,
                    actor=ev.actor,
                    previous_status=ev.previous_status,
                    new_status=ev.new_status,
                    details={"reason": ev.reason, "plan_hash": ev.plan_hash},
                    created_at=ev.created_at,
                )
            )

    # Executions
    if category in ("all", "execution"):
        res = await db.execute(
            select(ExecutionEvent)
            .order_by(desc(ExecutionEvent.created_at))
            .limit(limit + offset)
        )
        for ev in res.scalars().all():
            events.append(
                UnifiedAuditEventResponse(
                    id=ev.id,
                    category="execution",
                    event_type=ev.event_type,
                    resource_id=ev.execution_id,
                    incident_id=ev.incident_id,
                    actor=ev.actor,
                    previous_status=ev.previous_status,
                    new_status=ev.new_status,
                    details=ev.details or {},
                    created_at=ev.created_at,
                )
            )

    # Verifications
    if category in ("all", "verification"):
        res = await db.execute(
            select(VerificationEvent)
            .order_by(desc(VerificationEvent.created_at))
            .limit(limit + offset)
        )
        for ev in res.scalars().all():
            events.append(
                UnifiedAuditEventResponse(
                    id=ev.id,
                    category="verification",
                    event_type=ev.event_type,
                    resource_id=ev.verification_id,
                    incident_id=None,
                    actor=ev.actor,
                    previous_status=ev.previous_status,
                    new_status=ev.new_status,
                    details={**(ev.details or {}), "outcome": ev.outcome},
                    created_at=ev.created_at,
                )
            )

    # Rollback Assessments
    if category in ("all", "rollback"):
        res = await db.execute(
            select(RollbackEvent)
            .order_by(desc(RollbackEvent.created_at))
            .limit(limit + offset)
        )
        for ev in res.scalars().all():
            events.append(
                UnifiedAuditEventResponse(
                    id=ev.id,
                    category="rollback",
                    event_type=ev.event_type,
                    resource_id=ev.assessment_id,
                    incident_id=None,
                    actor=ev.actor,
                    previous_status=ev.previous_status,
                    new_status=ev.new_status,
                    details={
                        **(ev.details or {}),
                        "readiness_status": ev.readiness_status,
                    },
                    created_at=ev.created_at,
                )
            )

    # Sort all aggregated events descending by timestamp
    events.sort(key=lambda x: x.created_at, reverse=True)

    return events[offset : offset + limit]
