from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.verification_schemas import (
    VerificationDetailResponse,
    VerificationEventResponse,
    VerificationSummaryResponse,
    VerifyExecutionRequest,
)
from aegisops.core.auth import (
    AuthenticatedActor,
    get_current_actor,
    get_verifier_actor,
)
from aegisops.core.rate_limit import rate_limit_verifications
from aegisops.db.session import get_db
from aegisops.execution.registry import OperationNotAllowedError
from aegisops.observability.metrics import VERIFICATION_REQUESTS
from aegisops.services import verifications
from aegisops.services.executions import (
    ConcurrencyConflictError,
    ExecutionNotFoundError,
    IdempotencyConflictError,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.services.verifications import (
    VerificationEligibilityError,
)

router = APIRouter(tags=["Post-Execution Verification"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/executions/{execution_id}/verifications",
    response_model=VerificationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_verifications)],
)
async def create_execution_verification(
    execution_id: UUID,
    payload: VerifyExecutionRequest,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(get_verifier_actor)],
    db: DbSession,
):
    """Executes deterministic post-execution verification for a completed execution."""
    try:
        record, is_replay = await verifications.execute_verification(
            session=db,
            execution_id=execution_id,
            criteria=payload.criteria,
            idempotency_key=payload.idempotency_key,
            requested_by=actor.identity,
        )

        VERIFICATION_REQUESTS.labels(outcome=record.outcome).inc()

        if is_replay:
            response.status_code = status.HTTP_200_OK

        return VerificationDetailResponse(
            id=record.id,
            execution_id=record.execution_id,
            incident_id=record.incident_id,
            approval_id=record.approval_id,
            approved_plan_hash=record.approved_plan_hash,
            operation_id=record.operation_id,
            execution_mode=record.execution_mode,
            status=record.status,
            outcome=record.outcome,
            verification_criteria=record.verification_criteria,
            baseline_evidence=record.baseline_evidence,
            followup_evidence=record.followup_evidence,
            metric_comparison=record.metric_comparison,
            limitations=record.limitations,
            observations=record.observations,
            requested_by=record.requested_by,
            idempotency_key=record.idempotency_key,
            requested_at=record.requested_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_ms=record.duration_ms,
            human_review_required=record.human_review_required,
            remediation_success_confirmed=record.remediation_success_confirmed,
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
        VerificationEligibilityError,
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
    "/verifications",
    response_model=list[VerificationSummaryResponse],
)
async def list_execution_verifications(
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
    """Retrieves paginated post-execution verification history."""
    records = await verifications.list_verifications(
        session=db,
        execution_id=execution_id,
        incident_id=incident_id,
        limit=limit,
        offset=offset,
    )
    return [
        VerificationSummaryResponse(
            id=r.id,
            execution_id=r.execution_id,
            incident_id=r.incident_id,
            approval_id=r.approval_id,
            operation_id=r.operation_id,
            execution_mode=r.execution_mode,
            status=r.status,
            outcome=r.outcome,
            requested_by=r.requested_by,
            requested_at=r.requested_at,
            completed_at=r.completed_at,
            duration_ms=r.duration_ms,
            human_review_required=r.human_review_required,
            remediation_success_confirmed=r.remediation_success_confirmed,
        )
        for r in records
    ]


@router.get(
    "/verifications/{verification_id}",
    response_model=VerificationDetailResponse,
)
async def get_execution_verification(
    verification_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    """Retrieves detailed record of a single post-execution verification."""
    record = await verifications.get_verification(db, verification_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification record '{verification_id}' does not exist",
        )

    return VerificationDetailResponse(
        id=record.id,
        execution_id=record.execution_id,
        incident_id=record.incident_id,
        approval_id=record.approval_id,
        approved_plan_hash=record.approved_plan_hash,
        operation_id=record.operation_id,
        execution_mode=record.execution_mode,
        status=record.status,
        outcome=record.outcome,
        verification_criteria=record.verification_criteria,
        baseline_evidence=record.baseline_evidence,
        followup_evidence=record.followup_evidence,
        metric_comparison=record.metric_comparison,
        limitations=record.limitations,
        observations=record.observations,
        requested_by=record.requested_by,
        idempotency_key=record.idempotency_key,
        requested_at=record.requested_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_ms=record.duration_ms,
        human_review_required=record.human_review_required,
        remediation_success_confirmed=record.remediation_success_confirmed,
        error_message=record.error_message,
        is_replay=False,
    )


@router.get(
    "/verifications/{verification_id}/events",
    response_model=list[VerificationEventResponse],
)
async def list_verification_events(
    verification_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    """Retrieves append-only audit trail events for a verification record."""
    record = await verifications.get_verification(db, verification_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification record '{verification_id}' does not exist",
        )

    events = await verifications.get_verification_events(db, verification_id)
    return [
        VerificationEventResponse(
            id=e.id,
            verification_id=e.verification_id,
            execution_id=e.execution_id,
            actor=e.actor,
            event_type=e.event_type,
            previous_status=e.previous_status,
            new_status=e.new_status,
            outcome=e.outcome,
            details=e.details,
            created_at=e.created_at,
        )
        for e in events
    ]
