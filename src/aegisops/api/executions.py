from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.api.execution_schemas import (
    AllowlistedOperationResponse,
    DiagnoseExecutionRequest,
    ExecutionDetailResponse,
    ExecutionEventResponse,
    ExecutionResponse,
    SimulateExecutionRequest,
)
from aegisops.core.auth import (
    AuthenticatedActor,
    get_current_actor,
    get_executor_actor,
)
from aegisops.core.rate_limit import rate_limit_executions
from aegisops.db.session import get_db
from aegisops.domain.execution import ExecutionMode, ExecutionStatus
from aegisops.execution.registry import (
    ALLOWLISTED_OPERATIONS,
    OperationNotAllowedError,
)
from aegisops.observability.metrics import EXECUTION_REQUESTS
from aegisops.services import executions
from aegisops.services.executions import (
    ApprovalEligibilityError,
    ConcurrencyConflictError,
    ExecutionExpiredError,
    IdempotencyConflictError,
    LiveDiagnosticsDisabledError,
    ScopeValidationError,
)
from aegisops.services.plan_integrity import PlanIntegrityError

router = APIRouter(tags=["Remediation Executions"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/execution-operations",
    response_model=list[AllowlistedOperationResponse],
)
async def list_execution_operations(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
):
    """Returns the immutable server-side allowlist of available operations with mode capabilities."""
    return [
        AllowlistedOperationResponse(
            id=op.id,
            name=op.name,
            description=op.description,
            risk_level=op.risk_level,
            required_permission=op.required_permission,
            max_simulated_duration_ms=op.max_simulated_duration_ms,
            real_execution_supported=False,
            live_diagnostic_supported=op.live_diagnostic_supported,
            supported_modes=sorted(op.supported_modes),
            is_read_only=op.is_read_only,
            parameters_schema=op.parameters_schema.model_json_schema(),
        )
        for op in ALLOWLISTED_OPERATIONS.values()
    ]


@router.post(
    "/executions/simulate",
    response_model=ExecutionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_executions)],
)
async def simulate_remediation_execution(
    payload: SimulateExecutionRequest,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(get_executor_actor)],
    db: DbSession,
):
    """Executes a dry-run simulation of an allowlisted operation bound to an approved remediation plan."""
    try:
        record, is_replay = await executions.execute_simulation(
            session=db,
            approval_id=payload.approval_id,
            incident_id=payload.incident_id,
            operation_id=payload.operation_id,
            recommendation_index=payload.recommendation_index,
            parameters=payload.parameters,
            idempotency_key=payload.idempotency_key,
            requested_by=actor.identity,
        )

        EXECUTION_REQUESTS.labels(
            mode="simulation",
            operation=payload.operation_id,
            status="succeeded",
        ).inc()

        if is_replay:
            response.status_code = status.HTTP_200_OK

        return ExecutionDetailResponse(
            id=record.id,
            incident_id=record.incident_id,
            approval_id=record.approval_id,
            approved_plan_hash=record.approved_plan_hash,
            approved_plan_version=record.approved_plan_version,
            selected_recommendation_index=record.selected_recommendation_index,
            selected_recommendation_title=record.selected_recommendation_title,
            operation_id=record.operation_id,
            parameters=record.parameters,
            requested_by=record.requested_by,
            mode=ExecutionMode(record.mode),
            status=ExecutionStatus(record.status),
            idempotency_key=record.idempotency_key,
            requested_at=record.requested_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_ms=record.duration_ms,
            is_replay=is_replay,
            actual_infrastructure_access=False,
            system_changes_performed=False,
            simulation_result=record.simulation_result,
            diagnostic_result=None,
        )

    except (
        ApprovalEligibilityError,
        ConcurrencyConflictError,
        ExecutionExpiredError,
        IdempotencyConflictError,
        PlanIntegrityError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except LiveDiagnosticsDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except (
        OperationNotAllowedError,
        ScopeValidationError,
        ValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )


@router.post(
    "/executions/diagnose",
    response_model=ExecutionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_executions)],
)
async def diagnose_remediation_execution(
    payload: DiagnoseExecutionRequest,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(get_executor_actor)],
    db: DbSession,
):
    """Executes an authenticated read-only Prometheus live diagnostic bound to an approved remediation plan."""
    try:
        record, is_replay = await executions.execute_live_diagnostic(
            session=db,
            approval_id=payload.approval_id,
            incident_id=payload.incident_id,
            operation_id=payload.operation_id,
            recommendation_index=payload.recommendation_index,
            parameters=payload.parameters,
            idempotency_key=payload.idempotency_key,
            requested_by=actor.identity,
        )

        EXECUTION_REQUESTS.labels(
            mode="live_diagnostic",
            operation=payload.operation_id,
            status="succeeded",
        ).inc()

        if is_replay:
            response.status_code = status.HTTP_200_OK

        return ExecutionDetailResponse(
            id=record.id,
            incident_id=record.incident_id,
            approval_id=record.approval_id,
            approved_plan_hash=record.approved_plan_hash,
            approved_plan_version=record.approved_plan_version,
            selected_recommendation_index=record.selected_recommendation_index,
            selected_recommendation_title=record.selected_recommendation_title,
            operation_id=record.operation_id,
            parameters=record.parameters,
            requested_by=record.requested_by,
            mode=ExecutionMode(record.mode),
            status=ExecutionStatus(record.status),
            idempotency_key=record.idempotency_key,
            requested_at=record.requested_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_ms=record.duration_ms,
            is_replay=is_replay,
            actual_infrastructure_access=True,
            system_changes_performed=False,
            simulation_result=None,
            diagnostic_result=record.diagnostic_result,
        )

    except (
        ApprovalEligibilityError,
        ConcurrencyConflictError,
        ExecutionExpiredError,
        IdempotencyConflictError,
        PlanIntegrityError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except LiveDiagnosticsDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except (
        OperationNotAllowedError,
        ScopeValidationError,
        ValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )


@router.get(
    "/executions",
    response_model=list[ExecutionResponse],
)
async def list_executions(
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
    incident_id: UUID | None = None,
    approval_id: UUID | None = None,
    status_filter: Annotated[ExecutionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    records = await executions.list_executions(
        session=db,
        incident_id=incident_id,
        approval_id=approval_id,
        status=status_filter.value if status_filter else None,
        limit=limit,
        offset=offset,
    )
    return [
        ExecutionResponse(
            id=r.id,
            incident_id=r.incident_id,
            approval_id=r.approval_id,
            approved_plan_hash=r.approved_plan_hash,
            approved_plan_version=r.approved_plan_version,
            selected_recommendation_index=r.selected_recommendation_index,
            selected_recommendation_title=r.selected_recommendation_title,
            operation_id=r.operation_id,
            parameters=r.parameters,
            requested_by=r.requested_by,
            mode=ExecutionMode(r.mode),
            status=ExecutionStatus(r.status),
            idempotency_key=r.idempotency_key,
            requested_at=r.requested_at,
            started_at=r.started_at,
            completed_at=r.completed_at,
            duration_ms=r.duration_ms,
            is_replay=False,
            actual_infrastructure_access=(
                r.mode == ExecutionMode.LIVE_DIAGNOSTIC.value
            ),
            system_changes_performed=False,
        )
        for r in records
    ]


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionDetailResponse,
)
async def get_execution(
    execution_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    record = await executions.get_execution(db, execution_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution record {execution_id} not found",
        )
    return ExecutionDetailResponse(
        id=record.id,
        incident_id=record.incident_id,
        approval_id=record.approval_id,
        approved_plan_hash=record.approved_plan_hash,
        approved_plan_version=record.approved_plan_version,
        selected_recommendation_index=record.selected_recommendation_index,
        selected_recommendation_title=record.selected_recommendation_title,
        operation_id=record.operation_id,
        parameters=record.parameters,
        requested_by=record.requested_by,
        mode=ExecutionMode(record.mode),
        status=ExecutionStatus(record.status),
        idempotency_key=record.idempotency_key,
        requested_at=record.requested_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_ms=record.duration_ms,
        is_replay=False,
        actual_infrastructure_access=(
            record.mode == ExecutionMode.LIVE_DIAGNOSTIC.value
        ),
        system_changes_performed=False,
        simulation_result=record.simulation_result,
        diagnostic_result=record.diagnostic_result,
    )


@router.get(
    "/executions/{execution_id}/events",
    response_model=list[ExecutionEventResponse],
)
async def get_execution_events(
    execution_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(get_current_actor)],
    db: DbSession,
):
    record = await executions.get_execution(db, execution_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution record {execution_id} not found",
        )
    return await executions.get_execution_events(db, execution_id)
