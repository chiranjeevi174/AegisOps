import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.core.config import get_settings
from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.execution import (
    ExecutionMode,
    ExecutionStatus,
    RemediationExecution,
)
from aegisops.domain.execution_event import ExecutionEvent, ExecutionEventType
from aegisops.execution.diagnostics import (
    execute_diagnostic_operation,
)
from aegisops.execution.registry import (
    OperationNotAllowedError,
    get_operation_definition,
    validate_operation_parameters,
)
from aegisops.execution.simulator import simulate_operation
from aegisops.integrations.prometheus import PrometheusError
from aegisops.services.plan_integrity import PlanIntegrityError, verify_plan_integrity


class ExecutionNotFoundError(Exception):
    """Raised when an execution record does not exist."""


class ApprovalEligibilityError(Exception):
    """Raised when an approval is not eligible for execution."""


class ExecutionExpiredError(Exception):
    """Raised when an approved plan's execution authorization window has expired."""


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused with conflicting mode, operation, or parameters."""


class ConcurrencyConflictError(Exception):
    """Raised when an operation with the same idempotency key is currently running."""


class ScopeValidationError(Exception):
    """Raised when an operation exceeds or does not align with the approved plan scope."""


class LiveDiagnosticsDisabledError(Exception):
    """Raised when live diagnostics are disabled in application configuration."""


def _canonical_params(params: dict[str, Any]) -> str:
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


# Deterministic, explicit server-side operation-binding policy
OPERATION_BINDING_RULES: dict[str, dict[str, Any]] = {
    "inspect_service_health": {
        "allowed_action_types": {"diagnostic", "observation"},
        "keywords": {
            "service",
            "health",
            "availability",
            "uptime",
            "alive",
            "status",
            "endpoint",
            "healthcheck",
            "dependencies",
        },
    },
    "inspect_cpu_metrics": {
        "allowed_action_types": {"diagnostic", "observation"},
        "keywords": {
            "cpu",
            "processor",
            "core",
            "throttling",
            "utilization",
            "compute",
            "contention",
            "load",
        },
    },
    "inspect_latency_metrics": {
        "allowed_action_types": {"diagnostic", "observation"},
        "keywords": {
            "latency",
            "duration",
            "delay",
            "response time",
            "rtt",
            "pause",
            "slowness",
            "slowdown",
        },
    },
    "inspect_error_rate": {
        "allowed_action_types": {"diagnostic", "observation"},
        "keywords": {
            "error",
            "5xx",
            "fault",
            "failure",
            "exception",
            "status code",
            "ratio",
            "rate",
            "spike",
        },
    },
    "review_service_configuration": {
        "allowed_action_types": {"configuration_review"},
        "keywords": {
            "configuration",
            "config",
            "settings",
            "jvm",
            "flags",
            "thread pool",
            "heap",
            "memory limit",
            "runtime",
        },
    },
}


def verify_recommendation_binding(
    operation_id: str,
    recommendation: dict[str, Any],
) -> None:
    """Deterministic server-side verification that an operation is authorized by the recommendation.

    Fails closed if the binding cannot be verified unambiguously.
    """
    rule = OPERATION_BINDING_RULES.get(operation_id)
    if rule is None:
        raise ScopeValidationError(
            f"Operation '{operation_id}' has no defined authorization binding rule"
        )

    # 1. Check explicit bound operation if specified on recommendation
    explicit_bound_op = recommendation.get("bound_operation_id") or recommendation.get(
        "operation_id"
    )
    if explicit_bound_op:
        if explicit_bound_op != operation_id:
            raise ScopeValidationError(
                f"Operation '{operation_id}' does not match recommendation's bound operation '{explicit_bound_op}'"
            )
        return

    # 2. Verify recommendation action_type compatibility
    action_type = recommendation.get("action_type")
    allowed_types = rule["allowed_action_types"]
    if action_type not in allowed_types:
        raise ScopeValidationError(
            f"Operation '{operation_id}' requires recommendation action_type in {sorted(allowed_types)}, "
            f"but approved recommendation has action_type '{action_type}'"
        )

    # 3. Verify deterministic keyword binding against title and description
    title = str(recommendation.get("title", "")).lower()
    description = str(recommendation.get("description", "")).lower()
    text_corpus = f"{title} {description}"

    matched_keywords = [kw for kw in rule["keywords"] if kw in text_corpus]
    if not matched_keywords:
        raise ScopeValidationError(
            f"Operation '{operation_id}' is outside the authorized scope of recommendation "
            f"'{recommendation.get('title', 'Unknown')}' (no required scope keywords matched)"
        )


async def validate_approval_eligibility(
    session: AsyncSession,
    approval_id: UUID,
    incident_id: UUID,
    operation_id: str,
    recommendation_index: int,
    actor_identity: str,
    mode: ExecutionMode = ExecutionMode.SIMULATION,
) -> tuple[RemediationApproval, str]:
    """Validates approval state, integrity, expiration window, and scope binding."""
    # 1. Load approval
    approval = await session.get(RemediationApproval, approval_id)
    if approval is None:
        raise ApprovalEligibilityError(f"Approval request {approval_id} not found")

    # 2. Verify incident association
    if approval.incident_id != incident_id:
        raise ApprovalEligibilityError(
            f"Approval {approval_id} belongs to incident {approval.incident_id}, not {incident_id}"
        )

    # 3. Verify approval status is approved
    if approval.status != ApprovalStatus.APPROVED.value:
        raise ApprovalEligibilityError(
            f"Approval {approval_id} is in '{approval.status}' status (must be 'approved')"
        )

    # 4. Verify plan integrity hash
    if not verify_plan_integrity(approval.plan_snapshot, approval.plan_hash):
        raise PlanIntegrityError(
            f"Plan integrity verification failed for approval {approval_id}"
        )

    # 5. Verify execution authorization window
    now = datetime.now(UTC)
    decided_at = approval.decided_at or approval.requested_at
    eligibility_window = timedelta(minutes=get_settings().execution_eligibility_minutes)
    if now - decided_at > eligibility_window:
        raise ExecutionExpiredError(
            f"Execution authorization window expired at {(decided_at + eligibility_window).isoformat()} "
            f"({get_settings().execution_eligibility_minutes}m policy)"
        )

    # 6. Verify operation allowlist and mode support
    op_def = get_operation_definition(operation_id)
    if op_def.real_execution_supported:
        raise OperationNotAllowedError(
            "Mutating execution is forbidden; only simulation and read-only diagnostics are supported"
        )

    if mode == ExecutionMode.SIMULATION:
        if ExecutionMode.SIMULATION.value not in op_def.supported_modes:
            raise OperationNotAllowedError(
                f"Operation '{operation_id}' does not support simulation mode"
            )
    elif mode == ExecutionMode.LIVE_DIAGNOSTIC:
        if not get_settings().live_diagnostics_enabled:
            raise LiveDiagnosticsDisabledError(
                "Live diagnostics are disabled in application configuration"
            )
        if not op_def.live_diagnostic_supported:
            raise OperationNotAllowedError(
                f"Operation '{operation_id}' does not support live diagnostic mode"
            )
        if ExecutionMode.LIVE_DIAGNOSTIC.value not in op_def.supported_modes:
            raise OperationNotAllowedError(
                f"Operation '{operation_id}' does not support live diagnostic mode"
            )

    # 7. Verify recommendation index and deterministic scope binding
    actions = approval.plan_snapshot.get("recommended_actions", [])
    if not actions:
        raise ScopeValidationError(
            "Approved plan snapshot contains no recommended actions"
        )

    if recommendation_index < 1 or recommendation_index > len(actions):
        raise ScopeValidationError(
            f"Recommendation index {recommendation_index} is out of bounds (1 to {len(actions)})"
        )

    recommendation = actions[recommendation_index - 1]
    verify_recommendation_binding(operation_id, recommendation)

    recommendation_title = recommendation.get("title", f"Action {recommendation_index}")
    return approval, recommendation_title


async def execute_simulation(
    session: AsyncSession,
    approval_id: UUID,
    incident_id: UUID,
    operation_id: str,
    recommendation_index: int,
    parameters: dict[str, Any],
    idempotency_key: str,
    requested_by: str,
) -> tuple[RemediationExecution, bool]:
    """Coordinates approval validation, idempotency checks, simulation execution, and atomic persistence.

    Returns (execution_record, is_replay).
    """
    if not idempotency_key or not idempotency_key.strip():
        raise ValueError("An idempotency key is required")

    idempotency_key = idempotency_key.strip()

    # 1. Validate operation parameters early
    validated_params = validate_operation_parameters(operation_id, parameters)

    # 2. Check idempotency (mode-aware)
    existing_stmt = select(RemediationExecution).where(
        RemediationExecution.approval_id == approval_id,
        RemediationExecution.idempotency_key == idempotency_key,
    )
    existing = await session.scalar(existing_stmt)
    if existing is not None:
        if existing.status in (
            ExecutionStatus.PENDING.value,
            ExecutionStatus.RUNNING.value,
        ):
            raise ConcurrencyConflictError(
                f"An execution with idempotency key '{idempotency_key}' is already in progress"
            )

        if (
            existing.mode == ExecutionMode.SIMULATION.value
            and existing.operation_id == operation_id
            and existing.selected_recommendation_index == recommendation_index
            and _canonical_params(existing.parameters)
            == _canonical_params(validated_params)
        ):
            return existing, True

        raise IdempotencyConflictError(
            f"Idempotency key '{idempotency_key}' already used with conflicting mode, operation, or parameters"
        )

    # 3. Validate approval eligibility and plan binding
    approval, recommendation_title = await validate_approval_eligibility(
        session=session,
        approval_id=approval_id,
        incident_id=incident_id,
        operation_id=operation_id,
        recommendation_index=recommendation_index,
        actor_identity=requested_by,
        mode=ExecutionMode.SIMULATION,
    )

    now = datetime.now(UTC)
    start_time = time.perf_counter()

    # 4. Run dry-run simulation
    sim_result = simulate_operation(operation_id, validated_params)

    end_time = time.perf_counter()
    duration_ms = max(1, int((end_time - start_time) * 1000))
    completed_at = datetime.now(UTC)

    # 5. Persist execution record and audit event atomically
    execution = RemediationExecution(
        incident_id=incident_id,
        approval_id=approval_id,
        approved_plan_hash=approval.plan_hash,
        approved_plan_version=approval.version,
        selected_recommendation_index=recommendation_index,
        selected_recommendation_title=recommendation_title,
        operation_id=operation_id,
        parameters=validated_params,
        requested_by=requested_by,
        mode=ExecutionMode.SIMULATION.value,
        status=ExecutionStatus.SIMULATED.value,
        idempotency_key=idempotency_key,
        requested_at=now,
        started_at=now,
        completed_at=completed_at,
        simulation_result=sim_result.model_dump(mode="json"),
        diagnostic_result=None,
        duration_ms=duration_ms,
    )
    session.add(execution)
    await session.flush()

    audit_event = ExecutionEvent(
        execution_id=execution.id,
        incident_id=incident_id,
        approval_id=approval_id,
        actor=requested_by,
        event_type=ExecutionEventType.SIMULATION_COMPLETED.value,
        previous_status=None,
        new_status=ExecutionStatus.SIMULATED.value,
        operation_id=operation_id,
        approved_plan_hash=approval.plan_hash,
        details={
            "idempotency_key": idempotency_key,
            "recommendation_index": recommendation_index,
            "recommendation_title": recommendation_title,
            "mode": ExecutionMode.SIMULATION.value,
            "duration_ms": duration_ms,
            "actual_infrastructure_access": False,
            "system_changes_performed": False,
        },
        created_at=completed_at,
    )
    session.add(audit_event)

    await session.commit()
    await session.refresh(execution)
    return execution, False


async def execute_live_diagnostic(
    session: AsyncSession,
    approval_id: UUID,
    incident_id: UUID,
    operation_id: str,
    recommendation_index: int,
    parameters: dict[str, Any],
    idempotency_key: str,
    requested_by: str,
) -> tuple[RemediationExecution, bool]:
    """Coordinates approval validation, idempotency checks, live Prometheus diagnostic execution, and audit persistence.

    Network calls to Prometheus are executed outside open DB transactions.
    Returns (execution_record, is_replay).
    """
    if not get_settings().live_diagnostics_enabled:
        raise LiveDiagnosticsDisabledError(
            "Live diagnostics are disabled in application configuration"
        )

    if not idempotency_key or not idempotency_key.strip():
        raise ValueError("An idempotency key is required")

    idempotency_key = idempotency_key.strip()

    # 1. Validate operation parameters early
    validated_params = validate_operation_parameters(operation_id, parameters)

    # 2. Check operation definition
    op_def = get_operation_definition(operation_id)
    if not op_def.live_diagnostic_supported:
        raise OperationNotAllowedError(
            f"Operation '{operation_id}' does not support live diagnostics"
        )

    # 3. Check idempotency and concurrency (mode-aware)
    existing_stmt = select(RemediationExecution).where(
        RemediationExecution.approval_id == approval_id,
        RemediationExecution.idempotency_key == idempotency_key,
    )
    existing = await session.scalar(existing_stmt)
    if existing is not None:
        if existing.status in (
            ExecutionStatus.PENDING.value,
            ExecutionStatus.RUNNING.value,
        ):
            raise ConcurrencyConflictError(
                f"A diagnostic execution with idempotency key '{idempotency_key}' is already in progress"
            )

        if (
            existing.mode == ExecutionMode.LIVE_DIAGNOSTIC.value
            and existing.operation_id == operation_id
            and existing.selected_recommendation_index == recommendation_index
            and _canonical_params(existing.parameters)
            == _canonical_params(validated_params)
        ):
            return existing, True

        raise IdempotencyConflictError(
            f"Idempotency key '{idempotency_key}' already used with conflicting mode, operation, or parameters"
        )

    # 4. Validate approval eligibility and plan binding
    approval, recommendation_title = await validate_approval_eligibility(
        session=session,
        approval_id=approval_id,
        incident_id=incident_id,
        operation_id=operation_id,
        recommendation_index=recommendation_index,
        actor_identity=requested_by,
        mode=ExecutionMode.LIVE_DIAGNOSTIC,
    )

    now = datetime.now(UTC)

    # 5. Persist RUNNING record and commit to prevent concurrent duplicates and release DB lock during network call
    execution = RemediationExecution(
        incident_id=incident_id,
        approval_id=approval_id,
        approved_plan_hash=approval.plan_hash,
        approved_plan_version=approval.version,
        selected_recommendation_index=recommendation_index,
        selected_recommendation_title=recommendation_title,
        operation_id=operation_id,
        parameters=validated_params,
        requested_by=requested_by,
        mode=ExecutionMode.LIVE_DIAGNOSTIC.value,
        status=ExecutionStatus.RUNNING.value,
        idempotency_key=idempotency_key,
        requested_at=now,
        started_at=now,
        completed_at=now,
        simulation_result=None,
        diagnostic_result=None,
        duration_ms=0,
    )
    session.add(execution)
    await session.flush()

    start_event = ExecutionEvent(
        execution_id=execution.id,
        incident_id=incident_id,
        approval_id=approval_id,
        actor=requested_by,
        event_type=ExecutionEventType.DIAGNOSTIC_STARTED.value,
        previous_status=None,
        new_status=ExecutionStatus.RUNNING.value,
        operation_id=operation_id,
        approved_plan_hash=approval.plan_hash,
        details={
            "idempotency_key": idempotency_key,
            "recommendation_index": recommendation_index,
            "recommendation_title": recommendation_title,
            "mode": ExecutionMode.LIVE_DIAGNOSTIC.value,
            "actual_infrastructure_access": True,
            "system_changes_performed": False,
        },
        created_at=now,
    )
    session.add(start_event)
    await session.commit()
    execution_id = execution.id

    # 6. Execute Prometheus diagnostic network call outside open DB transaction
    start_time = time.perf_counter()
    diagnostic_error: str | None = None
    diag_result = None

    try:
        diag_result = execute_diagnostic_operation(operation_id, validated_params)
    except (PrometheusError, TimeoutError) as exc:
        diagnostic_error = f"Prometheus diagnostic failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        diagnostic_error = f"Unexpected diagnostic failure: {type(exc).__name__}: {exc}"

    end_time = time.perf_counter()
    duration_ms = max(1, int((end_time - start_time) * 1000))
    completed_at = datetime.now(UTC)

    # 7. Persist terminal results and audit event atomically in DB
    exec_record = await session.get(RemediationExecution, execution_id)
    if exec_record is None:
        raise ExecutionNotFoundError(f"Execution record {execution_id} disappeared")

    exec_record.completed_at = completed_at
    exec_record.duration_ms = duration_ms

    if diagnostic_error is not None or diag_result is None:
        exec_record.status = ExecutionStatus.FAILED.value
        exec_record.error_message = diagnostic_error
        terminal_event_type = ExecutionEventType.DIAGNOSTIC_FAILED.value
        terminal_details = {
            "error": diagnostic_error,
            "mode": ExecutionMode.LIVE_DIAGNOSTIC.value,
            "actual_infrastructure_access": True,
            "system_changes_performed": False,
            "duration_ms": duration_ms,
        }
    else:
        exec_record.status = ExecutionStatus.DIAGNOSED.value
        exec_record.diagnostic_result = diag_result.model_dump(mode="json")
        terminal_event_type = ExecutionEventType.DIAGNOSTIC_COMPLETED.value
        terminal_details = {
            "mode": ExecutionMode.LIVE_DIAGNOSTIC.value,
            "duration_ms": duration_ms,
            "actual_infrastructure_access": True,
            "system_changes_performed": False,
            "data_availability_status": diag_result.data_availability_status,
            "metric_identifier": diag_result.metric_identifier,
        }

    completion_event = ExecutionEvent(
        execution_id=exec_record.id,
        incident_id=incident_id,
        approval_id=approval_id,
        actor=requested_by,
        event_type=terminal_event_type,
        previous_status=ExecutionStatus.RUNNING.value,
        new_status=exec_record.status,
        operation_id=operation_id,
        approved_plan_hash=approval.plan_hash,
        details=terminal_details,
        created_at=completed_at,
    )
    session.add(completion_event)

    await session.commit()
    await session.refresh(exec_record)
    return exec_record, False


async def reconcile_stale_executions(
    session: AsyncSession,
    threshold_minutes: int = 5,
) -> int:
    """Documented Worker Interruption Recovery Policy:

    If an execution process crashes, restarts, or is interrupted while accessing Prometheus,
    an execution record may remain indefinitely in RUNNING status.
    This reconciliation job marks any executions running longer than `threshold_minutes`
    as TIMED_OUT, preserving audit accountability and freeing idempotency locks.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=threshold_minutes)
    stmt = select(RemediationExecution).where(
        RemediationExecution.status.in_(
            [ExecutionStatus.RUNNING.value, ExecutionStatus.PENDING.value]
        ),
        RemediationExecution.started_at < cutoff,
    )
    stale_records = list((await session.scalars(stmt)).all())

    reconciled_count = 0
    now = datetime.now(UTC)
    for rec in stale_records:
        rec.status = ExecutionStatus.TIMED_OUT.value
        rec.completed_at = now
        rec.error_message = (
            f"Execution timed out or interrupted after {threshold_minutes} minutes"
        )

        timeout_event = ExecutionEvent(
            execution_id=rec.id,
            incident_id=rec.incident_id,
            approval_id=rec.approval_id,
            actor="system:reconciliation-worker",
            event_type=ExecutionEventType.TIMED_OUT.value,
            previous_status=ExecutionStatus.RUNNING.value,
            new_status=ExecutionStatus.TIMED_OUT.value,
            operation_id=rec.operation_id,
            approved_plan_hash=rec.approved_plan_hash,
            details={
                "reason": "Process interruption or timeout exceeded threshold",
                "threshold_minutes": threshold_minutes,
            },
            created_at=now,
        )
        session.add(timeout_event)
        reconciled_count += 1

    if reconciled_count > 0:
        await session.commit()

    return reconciled_count


async def get_execution(
    session: AsyncSession,
    execution_id: UUID,
) -> RemediationExecution | None:
    return await session.get(RemediationExecution, execution_id)


async def list_executions(
    session: AsyncSession,
    incident_id: UUID | None = None,
    approval_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RemediationExecution]:
    stmt = select(RemediationExecution).order_by(
        desc(RemediationExecution.requested_at),
        desc(RemediationExecution.id),
    )
    if incident_id is not None:
        stmt = stmt.where(RemediationExecution.incident_id == incident_id)
    if approval_id is not None:
        stmt = stmt.where(RemediationExecution.approval_id == approval_id)
    if status is not None:
        stmt = stmt.where(RemediationExecution.status == status)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.scalars(stmt)
    return list(result.all())


async def get_execution_events(
    session: AsyncSession,
    execution_id: UUID,
) -> list[ExecutionEvent]:
    stmt = (
        select(ExecutionEvent)
        .where(ExecutionEvent.execution_id == execution_id)
        .order_by(ExecutionEvent.created_at.asc())
    )
    result = await session.scalars(stmt)
    return list(result.all())
