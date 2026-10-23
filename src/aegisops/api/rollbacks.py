from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.rollback_schemas import (
    CreateRollbackAssessmentRequest,
    RollbackAssessmentDetailResponse,
    RollbackAssessmentSummaryResponse,
    RollbackEventResponse,
)
from aegisops.core.auth import (
    AuthenticatedActor,
    get_current_actor,
    get_rollback_assessor_actor,
)
from aegisops.core.rate_limit import rate_limit_rollbacks
from aegisops.db.session import get_db
from aegisops.execution.registry import OperationNotAllowedError
from aegisops.observability.metrics import ROLLBACK_ASSESSMENTS
from aegisops.rollback.eligibility import RollbackEligibilityError
from aegisops.services import rollbacks
from aegisops.services.executions import (
    ConcurrencyConflictError,
    ExecutionNotFoundError,
    IdempotencyConflictError,
)
from aegisops.services.plan_integrity import PlanIntegrityError

router = APIRouter(tags=["Rollback Readiness Framework"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/executions/{execution_id}/rollback-assessments",
    response_model=RollbackAssessmentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_rollbacks)],
)
async def create_rollback_assessment(
    execution_id: UUID,
    payload: CreateRollbackAssessmentRequest,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(get_rollback_assessor_actor)],
    db: DbSession,
):
    """Executes deterministic rollback readiness evaluation and simulation-only planning."""
    try:
        record, is_replay = await rollbacks.assess_rollback_readiness(
            session=db,
            execution_id=execution_id,
            idempotency_key=payload.idempotency_key,
            requested_by=actor.identity,
        )

        ROLLBACK_ASSESSMENTS.labels(readiness=record.readiness_status).inc()

        if is_replay:
            response.status_code = status.HTTP_200_OK

        return RollbackAssessmentDetailResponse(
            id=record.id,
            execution_id=record.execution_id,
            incident_id=record.incident_id,
            approval_id=record.approval_id,
            approved_plan_hash=record.approved_plan_hash,
            operation_id=record.operation_id,
            execution_mode=record.execution_mode,
            status=record.status,
            readiness_status=record.readiness_status,
            applicability=record.applicability,
            risk_level=record.risk_level,
            assessment_data=record.assessment_data,
            simulation_result=record.simulation_result,
            limitations=record.limitations,
            observations=record.observations,
            requested_by=record.requested_by,
            idempotency_key=record.idempotency_key,
            requested_at=record.requested_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_ms=record.duration_ms,
            human_authorization_required=record.human_authorization_required,
            rollback_execution_enabled=record.rollback_execution_enabled,
            system_changes_performed=record.system_changes_performed,
            error_message=record.error_message,
            is_replay=is_replay,
        )

    except ExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except (
        ConcurrencyConflictError,
        IdempotencyConflictError,
        PlanIntegrityError,
        RollbackEligibilityError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except (OperationNotAllowedError, ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )


@router.get(
    "/rollback-assessments",
    response_model=list[RollbackAssessmentSummaryResponse],
)
async def list_rollback_assessments(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
    execution_id: Annotated[
        UUID | None, Query(description="Filter by execution UUID")
    ] = None,
    incident_id: Annotated[
        UUID | None, Query(description="Filter by incident UUID")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Retrieves paginated rollback readiness assessment history."""
    records = await rollbacks.list_rollback_assessments(
        session=db,
        execution_id=execution_id,
        incident_id=incident_id,
        limit=limit,
        offset=offset,
    )
    return [
        RollbackAssessmentSummaryResponse(
            id=r.id,
            execution_id=r.execution_id,
            incident_id=r.incident_id,
            approval_id=r.approval_id,
            operation_id=r.operation_id,
            execution_mode=r.execution_mode,
            status=r.status,
            readiness_status=r.readiness_status,
            applicability=r.applicability,
            risk_level=r.risk_level,
            requested_by=r.requested_by,
            requested_at=r.requested_at,
            completed_at=r.completed_at,
            duration_ms=r.duration_ms,
            human_authorization_required=r.human_authorization_required,
            rollback_execution_enabled=r.rollback_execution_enabled,
            system_changes_performed=r.system_changes_performed,
        )
        for r in records
    ]


@router.get(
    "/rollback-assessments/{assessment_id}",
    response_model=RollbackAssessmentDetailResponse,
)
async def get_rollback_assessment_details(
    assessment_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    """Retrieves full details of a specific rollback readiness assessment."""
    record = await rollbacks.get_rollback_assessment(db, assessment_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rollback assessment '{assessment_id}' not found",
        )

    return RollbackAssessmentDetailResponse(
        id=record.id,
        execution_id=record.execution_id,
        incident_id=record.incident_id,
        approval_id=record.approval_id,
        approved_plan_hash=record.approved_plan_hash,
        operation_id=record.operation_id,
        execution_mode=record.execution_mode,
        status=record.status,
        readiness_status=record.readiness_status,
        applicability=record.applicability,
        risk_level=record.risk_level,
        assessment_data=record.assessment_data,
        simulation_result=record.simulation_result,
        limitations=record.limitations,
        observations=record.observations,
        requested_by=record.requested_by,
        idempotency_key=record.idempotency_key,
        requested_at=record.requested_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_ms=record.duration_ms,
        human_authorization_required=record.human_authorization_required,
        rollback_execution_enabled=record.rollback_execution_enabled,
        system_changes_performed=record.system_changes_performed,
        error_message=record.error_message,
        is_replay=False,
    )


@router.get(
    "/rollback-assessments/{assessment_id}/events",
    response_model=list[RollbackEventResponse],
)
async def get_rollback_assessment_events(
    assessment_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    """Retrieves immutable audit history events for a rollback readiness assessment."""
    record = await rollbacks.get_rollback_assessment(db, assessment_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rollback assessment '{assessment_id}' not found",
        )

    events = await rollbacks.get_rollback_assessment_events(db, assessment_id)
    return [
        RollbackEventResponse(
            id=e.id,
            assessment_id=e.assessment_id,
            execution_id=e.execution_id,
            actor=e.actor,
            event_type=e.event_type,
            previous_status=e.previous_status,
            new_status=e.new_status,
            readiness_status=e.readiness_status,
            details=e.details,
            created_at=e.created_at,
        )
        for e in events
    ]
