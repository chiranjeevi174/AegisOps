import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.domain.rollback import (
    RollbackApplicability,
    RollbackAssessment,
    RollbackAssessmentStatus,
    RollbackReadinessStatus,
    RollbackRiskLevel,
)
from aegisops.domain.rollback_event import RollbackEvent, RollbackEventType
from aegisops.rollback.eligibility import (
    evaluate_rollback_eligibility,
    validate_execution_for_rollback_eligibility,
)
from aegisops.rollback.risk import assess_rollback_risk
from aegisops.rollback.schemas import RollbackReadinessAssessment
from aegisops.rollback.simulator import simulate_rollback
from aegisops.services.executions import (
    ConcurrencyConflictError,
    IdempotencyConflictError,
)


class RollbackAssessmentNotFoundError(Exception):
    """Raised when a rollback readiness assessment record cannot be found."""


async def assess_rollback_readiness(
    session: AsyncSession,
    execution_id: UUID,
    idempotency_key: str,
    requested_by: str,
) -> tuple[RollbackAssessment, bool]:
    """Coordinates deterministic rollback readiness assessment with idempotency and safety controls.

    Strictly non-mutating: evaluates hypothetical reversibility, validates prerequisites,
    and records an immutable audit log.
    """
    started_time = datetime.now(UTC)
    t0 = time.perf_counter()

    # Phase 1: Pre-flight check & idempotency reservation
    query = select(RollbackAssessment).where(
        RollbackAssessment.execution_id == execution_id,
        RollbackAssessment.idempotency_key == idempotency_key,
    )
    res = await session.execute(query)
    existing = res.scalar_one_or_none()

    if existing:
        return existing, True

    # Check for another record with same idempotency key for a different execution
    conflict_query = select(RollbackAssessment).where(
        RollbackAssessment.idempotency_key == idempotency_key,
        RollbackAssessment.execution_id != execution_id,
    )
    conflict_res = await session.execute(conflict_query)
    if conflict_res.scalar_one_or_none():
        raise IdempotencyConflictError(
            f"Idempotency key '{idempotency_key}' already used for a different execution"
        )

    # Check concurrency: is there an active assessment running for this execution?
    active_query = select(RollbackAssessment).where(
        RollbackAssessment.execution_id == execution_id,
        RollbackAssessment.status == RollbackAssessmentStatus.RUNNING.value,
    )
    active_res = await session.execute(active_query)
    if active_res.scalar_one_or_none():
        raise ConcurrencyConflictError(
            f"Rollback readiness assessment for execution '{execution_id}' is already in progress"
        )

    # Validate execution integrity and eligibility
    (
        execution,
        approval,
        incident,
        verification,
    ) = await validate_execution_for_rollback_eligibility(
        session=session,
        execution_id=execution_id,
    )

    # Phase 2: Create initial RUNNING record and commit to reserve execution slot
    assessment = RollbackAssessment(
        execution_id=execution.id,
        incident_id=incident.id,
        approval_id=approval.id,
        approved_plan_hash=execution.approved_plan_hash,
        operation_id=execution.operation_id,
        execution_mode=execution.mode,
        status=RollbackAssessmentStatus.RUNNING.value,
        readiness_status=RollbackReadinessStatus.NOT_APPLICABLE.value,
        applicability=RollbackApplicability.NOT_APPLICABLE.value,
        risk_level=RollbackRiskLevel.LOW.value,
        assessment_data={},
        simulation_result=None,
        limitations=[],
        observations=[],
        requested_by=requested_by,
        idempotency_key=idempotency_key,
        requested_at=started_time,
        started_at=started_time,
        completed_at=started_time,
        duration_ms=0,
        human_authorization_required=True,
        rollback_execution_enabled=False,
        system_changes_performed=False,
        error_message=None,
    )
    session.add(assessment)
    await session.flush()

    start_event = RollbackEvent(
        assessment_id=assessment.id,
        execution_id=execution.id,
        actor=requested_by,
        event_type=RollbackEventType.STARTED.value,
        previous_status=None,
        new_status=RollbackAssessmentStatus.RUNNING.value,
        readiness_status=None,
        details={"operation_id": execution.operation_id, "mode": execution.mode},
        created_at=started_time,
    )
    session.add(start_event)
    await session.commit()
    assessment_id = assessment.id

    try:
        # Phase 3: Deterministic Readiness & Eligibility Evaluation
        (
            applicability,
            readiness_status,
            risk_level,
            prerequisites,
            evidence,
            missing_info,
            proposed_steps,
            validation_criteria,
            limitations,
            observations,
        ) = evaluate_rollback_eligibility(
            execution=execution,
            approval=approval,
            incident=incident,
            verification=verification,
        )

        # Risk assessment
        risk_level, risk_factors = assess_rollback_risk(
            execution=execution,
            applicability=applicability,
            prerequisites=prerequisites,
            verification=verification,
        )
        observations.extend(risk_factors)

        # Simulation
        simulation = simulate_rollback(
            execution=execution,
            applicability=applicability,
            risk_level=risk_level,
            prerequisites=prerequisites,
        )

        completed_time = datetime.now(UTC)
        duration_ms = max(1, int((time.perf_counter() - t0) * 1000))

        # Build validated Pydantic snapshot
        schema_snapshot = RollbackReadinessAssessment(
            assessment_id=assessment_id,
            execution_id=execution.id,
            incident_id=incident.id,
            approval_id=approval.id,
            operation_id=execution.operation_id,
            execution_mode=execution.mode,
            applicability=applicability.value,
            readiness_status=readiness_status.value,
            risk_level=risk_level.value,
            prerequisites=prerequisites,
            evidence_supporting_readiness=evidence,
            missing_information=missing_info,
            proposed_steps=proposed_steps,
            validation_criteria=validation_criteria,
            human_authorization_required=True,
            rollback_execution_enabled=False,
            system_changes_performed=False,
            limitations=limitations,
            observations=observations,
            simulation_result=simulation,
            assessed_at=completed_time,
        )

        # Phase 4: Atomically persist terminal assessment & audit events
        a_record = await session.get(RollbackAssessment, assessment_id)
        if not a_record:
            raise RollbackAssessmentNotFoundError(
                f"Rollback assessment '{assessment_id}' record disappeared"
            )

        a_record.status = RollbackAssessmentStatus.COMPLETED.value
        a_record.readiness_status = readiness_status.value
        a_record.applicability = applicability.value
        a_record.risk_level = risk_level.value
        a_record.assessment_data = schema_snapshot.model_dump(mode="json")
        a_record.simulation_result = simulation.model_dump(mode="json")
        a_record.limitations = limitations
        a_record.observations = observations
        a_record.completed_at = completed_time
        a_record.duration_ms = duration_ms

        complete_event = RollbackEvent(
            assessment_id=a_record.id,
            execution_id=a_record.execution_id,
            actor=requested_by,
            event_type=RollbackEventType.COMPLETED.value,
            previous_status=RollbackAssessmentStatus.RUNNING.value,
            new_status=RollbackAssessmentStatus.COMPLETED.value,
            readiness_status=readiness_status.value,
            details={
                "applicability": applicability.value,
                "readiness_status": readiness_status.value,
                "risk_level": risk_level.value,
                "human_authorization_required": True,
                "rollback_execution_enabled": False,
                "system_changes_performed": False,
            },
            created_at=completed_time,
        )
        session.add(complete_event)
        await session.commit()
        await session.refresh(a_record)
        return a_record, False

    except Exception as exc:
        failed_time = datetime.now(UTC)
        duration_ms = max(1, int((time.perf_counter() - t0) * 1000))
        fail_record = await session.get(RollbackAssessment, assessment_id)
        if fail_record:
            fail_record.status = RollbackAssessmentStatus.FAILED.value
            fail_record.readiness_status = RollbackReadinessStatus.BLOCKED.value
            fail_record.applicability = RollbackApplicability.UNSUPPORTED.value
            fail_record.risk_level = RollbackRiskLevel.HIGH.value
            fail_record.error_message = str(exc)
            fail_record.completed_at = failed_time
            fail_record.duration_ms = duration_ms

            fail_event = RollbackEvent(
                assessment_id=fail_record.id,
                execution_id=fail_record.execution_id,
                actor=requested_by,
                event_type=RollbackEventType.FAILED.value,
                previous_status=RollbackAssessmentStatus.RUNNING.value,
                new_status=RollbackAssessmentStatus.FAILED.value,
                readiness_status=RollbackReadinessStatus.BLOCKED.value,
                details={"error": str(exc)},
                created_at=failed_time,
            )
            session.add(fail_event)
            await session.commit()
        raise


async def get_rollback_assessment(
    session: AsyncSession,
    assessment_id: UUID,
) -> RollbackAssessment | None:
    return await session.get(RollbackAssessment, assessment_id)


async def get_rollback_assessment_events(
    session: AsyncSession,
    assessment_id: UUID,
) -> list[RollbackEvent]:
    query = (
        select(RollbackEvent)
        .where(RollbackEvent.assessment_id == assessment_id)
        .order_by(RollbackEvent.created_at.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_rollback_assessments(
    session: AsyncSession,
    execution_id: UUID | None = None,
    incident_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RollbackAssessment]:
    query = select(RollbackAssessment)
    if execution_id:
        query = query.where(RollbackAssessment.execution_id == execution_id)
    if incident_id:
        query = query.where(RollbackAssessment.incident_id == incident_id)

    query = (
        query.order_by(desc(RollbackAssessment.requested_at))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def reconcile_stale_rollback_assessments(
    session: AsyncSession,
    threshold_minutes: int = 5,
) -> int:
    """Recovers abandoned rollback assessment records that exceeded the staleness threshold."""
    cutoff = datetime.now(UTC) - timedelta(minutes=threshold_minutes)
    query = select(RollbackAssessment).where(
        RollbackAssessment.status == RollbackAssessmentStatus.RUNNING.value,
        RollbackAssessment.started_at < cutoff,
    )
    result = await session.execute(query)
    stale_records = result.scalars().all()

    count = 0
    now = datetime.now(UTC)
    for a in stale_records:
        a.status = RollbackAssessmentStatus.FAILED.value
        a.readiness_status = RollbackReadinessStatus.BLOCKED.value
        a.applicability = RollbackApplicability.UNSUPPORTED.value
        a.risk_level = RollbackRiskLevel.HIGH.value
        a.completed_at = now
        a.error_message = f"Assessment timed out after exceeding {threshold_minutes} minutes without response."

        event = RollbackEvent(
            assessment_id=a.id,
            execution_id=a.execution_id,
            actor="system_reconciliation",
            event_type=RollbackEventType.FAILED.value,
            previous_status=RollbackAssessmentStatus.RUNNING.value,
            new_status=RollbackAssessmentStatus.FAILED.value,
            readiness_status=RollbackReadinessStatus.BLOCKED.value,
            details={"reconciliation_reason": "worker_timeout_or_interruption"},
            created_at=now,
        )
        session.add(event)
        count += 1

    if count > 0:
        await session.commit()
    return count
