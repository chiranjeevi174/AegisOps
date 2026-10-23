import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.domain.approval import RemediationApproval
from aegisops.domain.execution import (
    ExecutionMode,
    ExecutionStatus,
    RemediationExecution,
)
from aegisops.domain.incident import Incident
from aegisops.domain.verification import (
    ExecutionVerification,
    VerificationOutcome,
    VerificationStatus,
)
from aegisops.domain.verification_event import (
    VerificationEvent,
    VerificationEventType,
)
from aegisops.execution.registry import get_operation_definition
from aegisops.services.executions import (
    ConcurrencyConflictError,
    ExecutionNotFoundError,
    IdempotencyConflictError,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.verification.comparison import compare_metric_observations
from aegisops.verification.evidence import (
    SIMULATOR_SCENARIO_LIMITATION,
    retrieve_baseline_evidence,
    retrieve_followup_evidence,
)
from aegisops.verification.schemas import (
    VerificationCriteria,
)


class VerificationEligibilityError(Exception):
    """Raised when an execution cannot be verified due to invalid state or eligibility."""


class VerificationNotFoundError(Exception):
    """Raised when a verification record cannot be found."""


def _canonical_criteria(criteria: VerificationCriteria) -> str:
    return json.dumps(
        criteria.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )


async def validate_execution_eligibility_for_verification(
    session: AsyncSession,
    execution_id: UUID,
) -> tuple[RemediationExecution, RemediationApproval, Incident]:
    """Validates execution integrity, association, and terminal readiness before verification."""
    execution = await session.get(RemediationExecution, execution_id)
    if not execution:
        raise ExecutionNotFoundError(
            f"Remediation execution '{execution_id}' does not exist"
        )

    # Associated approval check
    approval = await session.get(RemediationApproval, execution.approval_id)
    if not approval:
        raise VerificationEligibilityError(
            f"Referenced approval '{execution.approval_id}' for execution does not exist"
        )

    # Associated incident check
    incident = await session.get(Incident, execution.incident_id)
    if not incident:
        raise VerificationEligibilityError(
            f"Referenced incident '{execution.incident_id}' for execution does not exist"
        )

    # Immutable plan hash integrity check
    if execution.approved_plan_hash != approval.plan_hash:
        raise PlanIntegrityError(
            "Security violation: Execution approved plan hash does not match approval plan hash"
        )

    # Operation registered in allowlist
    get_operation_definition(execution.operation_id)

    # Execution status must be terminal
    terminal_statuses = {
        ExecutionStatus.SIMULATED.value,
        ExecutionStatus.DIAGNOSED.value,
        ExecutionStatus.FAILED.value,
        ExecutionStatus.TIMED_OUT.value,
        ExecutionStatus.REJECTED.value,
    }
    if execution.status not in terminal_statuses:
        raise VerificationEligibilityError(
            f"Execution is not in a terminal state (current status: '{execution.status}'). "
            "Verification requires completed execution records."
        )

    return execution, approval, incident


async def execute_verification(
    session: AsyncSession,
    execution_id: UUID,
    criteria: VerificationCriteria,
    idempotency_key: str,
    requested_by: str,
) -> tuple[ExecutionVerification, bool]:
    """Coordinates deterministic post-execution verification with idempotency and safety controls.

    Out-of-transaction network calls are used to avoid open database transactions during Prometheus queries.
    """
    canon_criteria = _canonical_criteria(criteria)
    started_time = datetime.now(UTC)
    t0 = time.perf_counter()

    # Phase 1: Pre-flight check & idempotency reservation
    query = select(ExecutionVerification).where(
        ExecutionVerification.execution_id == execution_id,
        ExecutionVerification.idempotency_key == idempotency_key,
    )
    res = await session.execute(query)
    existing = res.scalar_one_or_none()

    if existing:
        existing_canon = json.dumps(
            existing.verification_criteria, sort_keys=True, separators=(",", ":")
        )
        if existing_canon == canon_criteria:
            return existing, True
        raise IdempotencyConflictError(
            f"Idempotency key '{idempotency_key}' already used with conflicting verification criteria"
        )

    # Check concurrency: is there an active verification running?
    active_query = select(ExecutionVerification).where(
        ExecutionVerification.execution_id == execution_id,
        ExecutionVerification.status == VerificationStatus.RUNNING.value,
    )
    active_res = await session.execute(active_query)
    if active_res.scalar_one_or_none():
        raise ConcurrencyConflictError(
            f"Verification for execution '{execution_id}' is already in progress"
        )

    # Eligibility validation
    (
        execution,
        approval,
        incident,
    ) = await validate_execution_eligibility_for_verification(
        session=session,
        execution_id=execution_id,
    )

    # Mode branch: Simulation mode
    if execution.mode == ExecutionMode.SIMULATION.value:
        duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
        completed_time = datetime.now(UTC)

        verification = ExecutionVerification(
            execution_id=execution.id,
            incident_id=incident.id,
            approval_id=approval.id,
            approved_plan_hash=execution.approved_plan_hash,
            operation_id=execution.operation_id,
            execution_mode=execution.mode,
            status=VerificationStatus.COMPLETED.value,
            outcome=VerificationOutcome.NOT_APPLICABLE.value,
            verification_criteria=criteria.model_dump(mode="json"),
            baseline_evidence=None,
            followup_evidence=None,
            metric_comparison=None,
            limitations=[
                "Execution was conducted in simulation mode without accessing live infrastructure or retrieving live Prometheus measurements."
            ],
            observations=[
                "Simulation mode does not produce live telemetry for monitoring verification. Outcome is not applicable."
            ],
            requested_by=requested_by,
            idempotency_key=idempotency_key,
            requested_at=started_time,
            started_at=started_time,
            completed_at=completed_time,
            duration_ms=duration_ms,
            human_review_required=True,
            remediation_success_confirmed=False,
            error_message=None,
        )
        session.add(verification)
        await session.flush()

        event = VerificationEvent(
            verification_id=verification.id,
            execution_id=execution.id,
            actor=requested_by,
            event_type=VerificationEventType.COMPLETED.value,
            previous_status=None,
            new_status=VerificationStatus.COMPLETED.value,
            outcome=VerificationOutcome.NOT_APPLICABLE.value,
            details={
                "execution_mode": execution.mode,
                "outcome": VerificationOutcome.NOT_APPLICABLE.value,
                "remediation_success_confirmed": False,
                "human_review_required": True,
            },
            created_at=completed_time,
        )
        session.add(event)
        await session.commit()
        await session.refresh(verification)
        return verification, False

    # Non-diagnosed terminal status branch (e.g. failed or timed out during execution)
    if execution.status != ExecutionStatus.DIAGNOSED.value:
        duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
        completed_time = datetime.now(UTC)

        verification = ExecutionVerification(
            execution_id=execution.id,
            incident_id=incident.id,
            approval_id=approval.id,
            approved_plan_hash=execution.approved_plan_hash,
            operation_id=execution.operation_id,
            execution_mode=execution.mode,
            status=VerificationStatus.FAILED.value,
            outcome=VerificationOutcome.VERIFICATION_FAILED.value,
            verification_criteria=criteria.model_dump(mode="json"),
            baseline_evidence=None,
            followup_evidence=None,
            metric_comparison=None,
            limitations=[
                f"Execution did not achieve diagnosed status (terminal status was '{execution.status}')."
            ],
            observations=[
                f"Execution failure reason: {execution.error_message or 'Unknown execution failure'}"
            ],
            requested_by=requested_by,
            idempotency_key=idempotency_key,
            requested_at=started_time,
            started_at=started_time,
            completed_at=completed_time,
            duration_ms=duration_ms,
            human_review_required=True,
            remediation_success_confirmed=False,
            error_message=f"Execution terminal status was '{execution.status}'",
        )
        session.add(verification)
        await session.flush()

        event = VerificationEvent(
            verification_id=verification.id,
            execution_id=execution.id,
            actor=requested_by,
            event_type=VerificationEventType.FAILED.value,
            previous_status=None,
            new_status=VerificationStatus.FAILED.value,
            outcome=VerificationOutcome.VERIFICATION_FAILED.value,
            details={"execution_status": execution.status},
            created_at=completed_time,
        )
        session.add(event)
        await session.commit()
        await session.refresh(verification)
        return verification, False

    # Step 1: Create RUNNING record and commit to reserve execution slot
    verification = ExecutionVerification(
        execution_id=execution.id,
        incident_id=incident.id,
        approval_id=approval.id,
        approved_plan_hash=execution.approved_plan_hash,
        operation_id=execution.operation_id,
        execution_mode=execution.mode,
        status=VerificationStatus.RUNNING.value,
        outcome=VerificationOutcome.INCONCLUSIVE.value,
        verification_criteria=criteria.model_dump(mode="json"),
        baseline_evidence=None,
        followup_evidence=None,
        metric_comparison=None,
        limitations=[],
        observations=[],
        requested_by=requested_by,
        idempotency_key=idempotency_key,
        requested_at=started_time,
        started_at=started_time,
        completed_at=started_time,
        duration_ms=0,
        human_review_required=True,
        remediation_success_confirmed=False,
        error_message=None,
    )
    session.add(verification)
    await session.flush()

    start_event = VerificationEvent(
        verification_id=verification.id,
        execution_id=execution.id,
        actor=requested_by,
        event_type=VerificationEventType.STARTED.value,
        previous_status=None,
        new_status=VerificationStatus.RUNNING.value,
        outcome=None,
        details={"operation_id": execution.operation_id},
        created_at=started_time,
    )
    session.add(start_event)
    await session.commit()
    verification_id = verification.id

    # Phase 2: Prometheus Evidence Retrieval outside DB transaction
    all_limitations: list[str] = [SIMULATOR_SCENARIO_LIMITATION]

    baseline_obs, base_limits = retrieve_baseline_evidence(execution, criteria)
    all_limitations.extend(base_limits)

    followup_obs, post_limits = retrieve_followup_evidence(execution, criteria)
    all_limitations.extend(post_limits)

    comparison = compare_metric_observations(baseline_obs, followup_obs, criteria)

    # Determine structured outcome
    outcome: VerificationOutcome
    if (
        baseline_obs is None
        or followup_obs is None
        or (
            baseline_obs.data_availability == "error"
            or followup_obs.data_availability == "error"
        )
        or (
            baseline_obs.data_availability
            in ("no_data", "insufficient_samples", "insufficient_coverage")
            or followup_obs.data_availability
            in ("no_data", "insufficient_samples", "insufficient_coverage")
        )
        or not comparison.sample_sufficiency
        or comparison.direction == "insufficient_evidence"
    ):
        outcome = VerificationOutcome.INCONCLUSIVE
    else:
        outcome = VerificationOutcome.DIAGNOSTIC_VERIFIED

    observations: list[str] = list(comparison.evaluation_notes)
    if outcome == VerificationOutcome.DIAGNOSTIC_VERIFIED and baseline_obs is not None:
        observations.append(
            f"Diagnostic monitoring verified for operation '{execution.operation_id}'. "
            f"Valid baseline and follow-up evidence collected for metric '{baseline_obs.metric_name}'."
        )

    duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
    completed_time = datetime.now(UTC)

    # Phase 3: Atomically persist terminal verification results & audit event
    v_record = await session.get(ExecutionVerification, verification_id)
    if not v_record:
        raise VerificationNotFoundError(
            f"Verification '{verification_id}' record disappeared"
        )

    v_record.status = VerificationStatus.COMPLETED.value
    v_record.outcome = outcome.value
    v_record.baseline_evidence = (
        baseline_obs.model_dump(mode="json") if baseline_obs else None
    )
    v_record.followup_evidence = (
        followup_obs.model_dump(mode="json") if followup_obs else None
    )
    v_record.metric_comparison = comparison.model_dump(mode="json")
    v_record.limitations = all_limitations
    v_record.observations = observations
    v_record.completed_at = completed_time
    v_record.duration_ms = duration_ms

    complete_event = VerificationEvent(
        verification_id=v_record.id,
        execution_id=v_record.execution_id,
        actor=requested_by,
        event_type=VerificationEventType.COMPLETED.value,
        previous_status=VerificationStatus.RUNNING.value,
        new_status=VerificationStatus.COMPLETED.value,
        outcome=outcome.value,
        details={
            "outcome": outcome.value,
            "direction": comparison.direction,
            "remediation_success_confirmed": False,
            "human_review_required": True,
        },
        created_at=completed_time,
    )
    session.add(complete_event)
    await session.commit()
    await session.refresh(v_record)
    return v_record, False


async def get_verification(
    session: AsyncSession,
    verification_id: UUID,
) -> ExecutionVerification | None:
    return await session.get(ExecutionVerification, verification_id)


async def get_verification_events(
    session: AsyncSession,
    verification_id: UUID,
) -> list[VerificationEvent]:
    query = (
        select(VerificationEvent)
        .where(VerificationEvent.verification_id == verification_id)
        .order_by(VerificationEvent.created_at.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_verifications(
    session: AsyncSession,
    execution_id: UUID | None = None,
    incident_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ExecutionVerification]:
    query = select(ExecutionVerification)
    if execution_id:
        query = query.where(ExecutionVerification.execution_id == execution_id)
    if incident_id:
        query = query.where(ExecutionVerification.incident_id == incident_id)

    query = (
        query.order_by(desc(ExecutionVerification.requested_at))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def reconcile_stale_verifications(
    session: AsyncSession,
    threshold_minutes: int = 5,
) -> int:
    """Recovers abandoned verification records that exceeded the staleness threshold."""
    cutoff = datetime.now(UTC) - timedelta(minutes=threshold_minutes)
    query = select(ExecutionVerification).where(
        ExecutionVerification.status == VerificationStatus.RUNNING.value,
        ExecutionVerification.started_at < cutoff,
    )
    result = await session.execute(query)
    stale_records = result.scalars().all()

    count = 0
    now = datetime.now(UTC)
    for v in stale_records:
        v.status = VerificationStatus.TIMED_OUT.value
        v.outcome = VerificationOutcome.VERIFICATION_FAILED.value
        v.completed_at = now
        v.error_message = f"Verification timed out after exceeding {threshold_minutes} minutes without response."

        event = VerificationEvent(
            verification_id=v.id,
            execution_id=v.execution_id,
            actor="system_reconciliation",
            event_type=VerificationEventType.TIMED_OUT.value,
            previous_status=VerificationStatus.RUNNING.value,
            new_status=VerificationStatus.TIMED_OUT.value,
            outcome=VerificationOutcome.VERIFICATION_FAILED.value,
            details={"reconciliation_reason": "worker_timeout_or_interruption"},
            created_at=now,
        )
        session.add(event)
        count += 1

    if count > 0:
        await session.commit()
    return count
