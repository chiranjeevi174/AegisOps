from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.execution import (
    ExecutionMode,
    ExecutionStatus,
    RemediationExecution,
)
from aegisops.domain.incident import Incident
from aegisops.domain.rollback import (
    RollbackApplicability,
    RollbackAssessment,
    RollbackAssessmentStatus,
    RollbackReadinessStatus,
    RollbackRiskLevel,
)
from aegisops.domain.rollback_event import RollbackEventType
from aegisops.execution.registry import OperationNotAllowedError
from aegisops.rollback.eligibility import (
    RollbackEligibilityError,
    evaluate_rollback_eligibility,
    validate_execution_for_rollback_eligibility,
)
from aegisops.rollback.risk import assess_rollback_risk
from aegisops.rollback.schemas import (
    RollbackPrerequisite,
    RollbackReadinessAssessment,
    RollbackStep,
)
from aegisops.rollback.simulator import simulate_rollback
from aegisops.services import approvals, rollbacks
from aegisops.services.executions import (
    ConcurrencyConflictError,
    ExecutionNotFoundError,
    IdempotencyConflictError,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.workflows.remediation import RemediationAction, RemediationPlan

# =========================================================================
# Test Helpers and Builders
# =========================================================================


async def create_test_incident(session_factory) -> Incident:
    async with session_factory() as session:
        incident = Incident(
            title="Service latency and health degradation",
            description="High latency observed across endpoints.",
            severity="high",
            status="open",
            source="alertmanager",
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
        return incident


def build_plan_for_operation(operation_id: str) -> RemediationPlan:
    return RemediationPlan(
        incident_summary="Synthetic diagnostic inspection incident.",
        planning_basis="RCA findings requiring telemetry verification.",
        recommended_actions=[
            RemediationAction(
                title="Inspect API Response Latency",
                description="Latency distributions and curves.",
                rationale="Required for verification.",
                supporting_evidence=["Observed degradation"],
                prerequisites=["Monitoring access"],
                risk_level="low",
                action_type="diagnostic",  # pyright: ignore[reportArgumentType]
                validation_steps=["Telemetry verification"],
                rollback_considerations=["None required"],
                requires_human_approval=True,
            )
        ],
        missing_information=[],
        overall_risk="low",
        requires_human_approval=True,
        execution_enabled=False,
    )


async def create_test_approval(
    session_factory, incident_id, operation_id: str = "inspect_latency_metrics"
) -> RemediationApproval:
    plan = build_plan_for_operation(operation_id)
    now = datetime.now(UTC)
    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident_id,
            plan=plan,
            requested_by="sre-engineer-alice",
            validity_minutes=120,
        )
        approval.status = ApprovalStatus.APPROVED.value
        approval.decided_by = "sre-lead-charlie"
        approval.decided_at = now
        approval.decision_reason = "Approved for advisory diagnostic steps."
        await session.commit()
        await session.refresh(approval)
        return approval


async def create_test_execution(
    session_factory,
    incident_id,
    approval_id,
    operation_id: str = "inspect_latency_metrics",
    mode: ExecutionMode = ExecutionMode.LIVE_DIAGNOSTIC,
    status: ExecutionStatus = ExecutionStatus.DIAGNOSED,
    idempotency_key: str = "exec-rollback-test-01",
) -> RemediationExecution:
    now = datetime.now(UTC) - timedelta(minutes=5)
    async with session_factory() as session:
        appr = await session.get(RemediationApproval, approval_id)
        assert appr is not None

        execution = RemediationExecution(
            incident_id=incident_id,
            approval_id=approval_id,
            approved_plan_hash=appr.plan_hash,
            approved_plan_version=appr.version,
            selected_recommendation_index=1,
            selected_recommendation_title="Inspect API Response Latency",
            operation_id=operation_id,
            parameters={"window_minutes": 15, "step": "15s"},
            requested_by="sre-operator-dan",
            mode=mode.value,
            status=status.value,
            idempotency_key=idempotency_key,
            requested_at=now,
            started_at=now,
            completed_at=now + timedelta(seconds=2),
            simulation_result={"simulated_success": True}
            if mode == ExecutionMode.SIMULATION
            else None,
            diagnostic_result={
                "operation_id": operation_id,
                "execution_mode": mode.value,
                "actual_infrastructure_access": mode == ExecutionMode.LIVE_DIAGNOSTIC,
                "system_changes_performed": False,
                "data_availability_status": "available",
            }
            if mode == ExecutionMode.LIVE_DIAGNOSTIC
            else None,
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        return execution


# =========================================================================
# 1. Schema & Invariant Tests
# =========================================================================


def test_rollback_schemas_enforce_execution_disabled_false():
    """Verify rollback_execution_enabled must strictly remain False."""
    now = datetime.now(UTC)
    with pytest.raises(ValidationError) as exc_info:
        RollbackReadinessAssessment(
            assessment_id=uuid4(),
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_latency_metrics",
            execution_mode="live_diagnostic",
            applicability="not_applicable",
            readiness_status="not_applicable",
            risk_level="low",
            assessed_at=now,
            rollback_execution_enabled=True,  # type: ignore
        )
    assert "rollback_execution_enabled must strictly remain False" in str(
        exc_info.value
    )


def test_rollback_schemas_enforce_human_auth_required_true():
    """Verify human_authorization_required must strictly remain True."""
    now = datetime.now(UTC)
    with pytest.raises(ValidationError) as exc_info:
        RollbackReadinessAssessment(
            assessment_id=uuid4(),
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_latency_metrics",
            execution_mode="live_diagnostic",
            applicability="not_applicable",
            readiness_status="not_applicable",
            risk_level="low",
            assessed_at=now,
            human_authorization_required=False,  # type: ignore
        )
    assert "human_authorization_required must strictly remain True" in str(
        exc_info.value
    )


def test_rollback_schemas_enforce_system_changes_performed_false():
    """Verify system_changes_performed must strictly remain False."""
    now = datetime.now(UTC)
    with pytest.raises(ValidationError) as exc_info:
        RollbackReadinessAssessment(
            assessment_id=uuid4(),
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_latency_metrics",
            execution_mode="live_diagnostic",
            applicability="not_applicable",
            readiness_status="not_applicable",
            risk_level="low",
            assessed_at=now,
            system_changes_performed=True,  # type: ignore
        )
    assert "system_changes_performed must strictly remain False" in str(exc_info.value)


def test_rollback_schemas_valid_construction():
    """Verify valid construction of RollbackReadinessAssessment."""
    now = datetime.now(UTC)
    assessment = RollbackReadinessAssessment(
        assessment_id=uuid4(),
        execution_id=uuid4(),
        incident_id=uuid4(),
        approval_id=uuid4(),
        operation_id="inspect_latency_metrics",
        execution_mode="live_diagnostic",
        applicability="not_applicable",
        readiness_status="not_applicable",
        risk_level="low",
        prerequisites=[
            RollbackPrerequisite(name="Check A", description="Desc A", satisfied=True)
        ],
        proposed_steps=[
            RollbackStep(
                step_number=1,
                action_type="advisory",
                description="Review telemetry",
                target_component="API Gateway",
            )
        ],
        assessed_at=now,
    )
    assert assessment.rollback_execution_enabled is False
    assert assessment.human_authorization_required is True
    assert assessment.system_changes_performed is False
    assert assessment.applicability == "not_applicable"
    assert assessment.readiness_status == "not_applicable"


def test_rollback_schemas_invalid_readiness_status_rejected():
    """Verify that invalid readiness_status values are rejected."""
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        RollbackReadinessAssessment(
            assessment_id=uuid4(),
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_latency_metrics",
            execution_mode="live_diagnostic",
            applicability="not_applicable",
            readiness_status="ready_to_rollback",  # type: ignore
            risk_level="low",
            assessed_at=now,
        )


# =========================================================================
# 2. Eligibility & Assessment Logic Tests
# =========================================================================


@pytest.mark.asyncio
async def test_eligibility_live_diagnostic_returns_not_applicable(test_context):
    """Verify that completed live_diagnostic operations resolve to NOT_APPLICABLE."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory, incident.id, approval.id, mode=ExecutionMode.LIVE_DIAGNOSTIC
    )

    async with session_factory() as session:
        (
            exec_rec,
            appr_rec,
            inc_rec,
            v_rec,
        ) = await validate_execution_for_rollback_eligibility(session, execution.id)
        assert exec_rec.id == execution.id

        (
            applicability,
            readiness_status,
            risk_level,
            _prereqs,
            _evidence,
            _missing,
            _steps,
            _validation,
            limits,
            obs,
        ) = evaluate_rollback_eligibility(exec_rec, appr_rec, inc_rec, v_rec)

        assert applicability == RollbackApplicability.NOT_APPLICABLE
        assert readiness_status == RollbackReadinessStatus.NOT_APPLICABLE
        assert risk_level == RollbackRiskLevel.LOW
        assert any("zero infrastructure modifications" in lim for lim in limits)
        assert any("rollback is NOT APPLICABLE" in o for o in obs)


@pytest.mark.asyncio
async def test_eligibility_simulation_returns_not_applicable(test_context):
    """Verify that simulation executions resolve to NOT_APPLICABLE."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory, incident.id, approval.id, mode=ExecutionMode.SIMULATION
    )

    async with session_factory() as session:
        (
            exec_rec,
            appr_rec,
            inc_rec,
            v_rec,
        ) = await validate_execution_for_rollback_eligibility(session, execution.id)

        (
            applicability,
            readiness_status,
            risk_level,
            _,
            _,
            _,
            _,
            _,
            _limits,
            _,
        ) = evaluate_rollback_eligibility(exec_rec, appr_rec, inc_rec, v_rec)

        assert applicability == RollbackApplicability.NOT_APPLICABLE
        assert readiness_status == RollbackReadinessStatus.NOT_APPLICABLE
        assert risk_level == RollbackRiskLevel.LOW


@pytest.mark.asyncio
async def test_eligibility_missing_execution_rejected(test_context):
    """Verify that non-existent execution UUID raises ExecutionNotFoundError."""
    _, session_factory = test_context
    async with session_factory() as session:
        with pytest.raises(ExecutionNotFoundError):
            await validate_execution_for_rollback_eligibility(session, uuid4())


@pytest.mark.asyncio
async def test_eligibility_tampered_plan_hash_rejected(test_context):
    """Verify that mismatched plan hash raises PlanIntegrityError."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    async with session_factory() as session:
        exec_to_tamper = await session.get(RemediationExecution, execution.id)
        assert exec_to_tamper is not None
        exec_to_tamper.approved_plan_hash = "tampered" + "0" * 56
        await session.commit()

        with pytest.raises(PlanIntegrityError):
            await validate_execution_for_rollback_eligibility(session, execution.id)


@pytest.mark.asyncio
async def test_eligibility_running_execution_rejected(test_context):
    """Verify that non-terminal (running) execution cannot be assessed."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory, incident.id, approval.id, status=ExecutionStatus.RUNNING
    )

    async with session_factory() as session:
        with pytest.raises(RollbackEligibilityError) as exc_info:
            await validate_execution_for_rollback_eligibility(session, execution.id)
        assert "not in a terminal state" in str(exc_info.value)


@pytest.mark.asyncio
async def test_eligibility_unknown_operation_rejected(test_context):
    """Verify that an operation not registered in allowlist raises OperationNotAllowedError."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        operation_id="unknown_mutating_op",
    )

    async with session_factory() as session:
        with pytest.raises(OperationNotAllowedError):
            await validate_execution_for_rollback_eligibility(session, execution.id)


# =========================================================================
# 3. Risk & Simulation Tests
# =========================================================================


def test_risk_assessment_read_only_low():
    """Verify that read-only executions are deterministically assessed as LOW risk."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_latency_metrics",
        mode=ExecutionMode.LIVE_DIAGNOSTIC.value,
        status=ExecutionStatus.DIAGNOSED.value,
        started_at=now,
        completed_at=now,
    )
    risk, factors = assess_rollback_risk(
        execution=execution,
        applicability=RollbackApplicability.NOT_APPLICABLE,
        prerequisites=[],
        verification=None,
    )
    assert risk == RollbackRiskLevel.LOW
    assert any("operational risk is minimal" in f for f in factors)


def test_simulation_read_only_truthful():
    """Verify that simulation for read-only operation truthfully reports no rollback necessary."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_latency_metrics",
        mode=ExecutionMode.LIVE_DIAGNOSTIC.value,
        status=ExecutionStatus.DIAGNOSED.value,
        started_at=now,
        completed_at=now,
    )
    res = simulate_rollback(
        execution=execution,
        applicability=RollbackApplicability.NOT_APPLICABLE,
        risk_level=RollbackRiskLevel.LOW,
        prerequisites=[],
    )
    assert res.simulation_mode == "simulation_only"
    assert res.can_safely_simulate is True
    assert any(
        "no infrastructure rollback actions are necessary" in a
        for a in res.simulated_actions
    )
    assert "Original unmodified production baseline state" in res.simulated_target_state


# =========================================================================
# 4. Service & Persistence Tests
# =========================================================================


@pytest.mark.asyncio
async def test_assess_rollback_readiness_success_and_events(test_context):
    """Verify that rollback readiness assessment persists and creates audit events."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    async with session_factory() as session:
        record, is_replay = await rollbacks.assess_rollback_readiness(
            session=session,
            execution_id=execution.id,
            idempotency_key="rollback-test-key-01",
            requested_by="sre-operator-dan",
        )
        assert is_replay is False
        assert record.execution_id == execution.id
        assert record.status == RollbackAssessmentStatus.COMPLETED.value
        assert record.readiness_status == RollbackReadinessStatus.NOT_APPLICABLE.value
        assert record.applicability == RollbackApplicability.NOT_APPLICABLE.value
        assert record.risk_level == RollbackRiskLevel.LOW.value
        assert record.human_authorization_required is True
        assert record.rollback_execution_enabled is False
        assert record.system_changes_performed is False

        # Verify audit events
        events = await rollbacks.get_rollback_assessment_events(session, record.id)
        assert len(events) == 2
        assert events[0].event_type == RollbackEventType.STARTED.value
        assert events[1].event_type == RollbackEventType.COMPLETED.value
        assert (
            events[1].readiness_status == RollbackReadinessStatus.NOT_APPLICABLE.value
        )


@pytest.mark.asyncio
async def test_assess_rollback_readiness_idempotent_replay(test_context):
    """Verify that repeating an assessment with the same key returns the existing record."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    async with session_factory() as session:
        rec1, is_replay1 = await rollbacks.assess_rollback_readiness(
            session=session,
            execution_id=execution.id,
            idempotency_key="idempotent-rollback-01",
            requested_by="sre-operator-dan",
        )
        assert is_replay1 is False

        rec2, is_replay2 = await rollbacks.assess_rollback_readiness(
            session=session,
            execution_id=execution.id,
            idempotency_key="idempotent-rollback-01",
            requested_by="sre-operator-dan",
        )
        assert is_replay2 is True
        assert rec1.id == rec2.id


@pytest.mark.asyncio
async def test_assess_rollback_readiness_idempotency_conflict_rejected(test_context):
    """Verify that reusing the same key across different executions raises IdempotencyConflictError."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval1 = await create_test_approval(session_factory, incident.id)
    approval2 = await create_test_approval(session_factory, incident.id)
    execution1 = await create_test_execution(
        session_factory, incident.id, approval1.id, idempotency_key="exec-k1"
    )
    execution2 = await create_test_execution(
        session_factory, incident.id, approval2.id, idempotency_key="exec-k2"
    )

    async with session_factory() as session:
        await rollbacks.assess_rollback_readiness(
            session=session,
            execution_id=execution1.id,
            idempotency_key="shared-conflict-key-01",
            requested_by="sre-operator-dan",
        )

        with pytest.raises(IdempotencyConflictError):
            await rollbacks.assess_rollback_readiness(
                session=session,
                execution_id=execution2.id,
                idempotency_key="shared-conflict-key-01",
                requested_by="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_assess_rollback_readiness_concurrency_lock_protection(test_context):
    """Verify that a concurrent running assessment for the same execution fails closed."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    now = datetime.now(UTC)
    async with session_factory() as session:
        # Create an artificial RUNNING assessment
        running_assessment = RollbackAssessment(
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
            limitations=[],
            observations=[],
            requested_by="sre-operator-dan",
            idempotency_key="lock-key-01",
            requested_at=now,
            started_at=now,
            completed_at=now,
            duration_ms=0,
            human_authorization_required=True,
            rollback_execution_enabled=False,
            system_changes_performed=False,
        )
        session.add(running_assessment)
        await session.commit()

        with pytest.raises(ConcurrencyConflictError):
            await rollbacks.assess_rollback_readiness(
                session=session,
                execution_id=execution.id,
                idempotency_key="different-key-02",
                requested_by="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_stale_rollback_assessment_recovery_policy(test_context):
    """Verify that stale RUNNING assessments exceeding the timeout threshold are reconciled to FAILED."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    stale_time = datetime.now(UTC) - timedelta(minutes=15)
    async with session_factory() as session:
        stale_a = RollbackAssessment(
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
            limitations=[],
            observations=[],
            requested_by="sre-operator-dan",
            idempotency_key="stale-assessment-key-01",
            requested_at=stale_time,
            started_at=stale_time,
            completed_at=stale_time,
            duration_ms=0,
            human_authorization_required=True,
            rollback_execution_enabled=False,
            system_changes_performed=False,
        )
        session.add(stale_a)
        await session.commit()
        stale_id = stale_a.id

        reconciled = await rollbacks.reconcile_stale_rollback_assessments(
            session, threshold_minutes=5
        )
        assert reconciled == 1

        updated = await session.get(RollbackAssessment, stale_id)
        assert updated is not None
        assert updated.status == RollbackAssessmentStatus.FAILED.value
        assert updated.readiness_status == RollbackReadinessStatus.BLOCKED.value
        assert "timed out" in (updated.error_message or "")


@pytest.mark.asyncio
async def test_rollback_assessment_never_mutates_incident_or_approval(test_context):
    """Verify that performing a rollback assessment leaves incident and approval unmutated."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    async with session_factory() as session:
        await rollbacks.assess_rollback_readiness(
            session=session,
            execution_id=execution.id,
            idempotency_key="immutability-check-01",
            requested_by="sre-operator-dan",
        )

        inc_check = await session.get(Incident, incident.id)
        assert inc_check is not None
        assert inc_check.status == "open"

        appr_check = await session.get(RemediationApproval, approval.id)
        assert appr_check is not None
        assert appr_check.status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_rollback_assessment_retention_foreign_key_protection(test_context):
    """Verify that deleting an incident is rejected by ON DELETE RESTRICT on rollback assessments."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    async with session_factory() as session:
        await rollbacks.assess_rollback_readiness(
            session=session,
            execution_id=execution.id,
            idempotency_key="retention-protect-01",
            requested_by="sre-operator-dan",
        )

        # Attempt to delete incident
        inc_to_del = await session.get(Incident, incident.id)
        assert inc_to_del is not None
        await session.delete(inc_to_del)

        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


# =========================================================================
# 5. API Integration Tests
# =========================================================================


@pytest.mark.asyncio
async def test_api_assess_unauthenticated_rejected(test_context):
    """Verify that POST without Bearer token returns 401."""
    client, _ = test_context
    resp = await client.post(
        f"/api/v1/executions/{uuid4()}/rollback-assessments",
        json={"idempotency_key": "some-random-key-01"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_assess_insufficient_role_rejected(test_context):
    """Verify that an actor lacking rollback assessment permission returns 403."""
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    # viewer role lacks rollback assessment permission
    headers = {"Authorization": "Bearer aegisops-dev-viewer-token"}
    resp = await client.post(
        f"/api/v1/executions/{execution.id}/rollback-assessments",
        json={"idempotency_key": "insufficient-role-key-01"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "lacks rollback assessment permission" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_assess_nonexistent_execution_returns_404(test_context):
    """Verify that requesting assessment on a missing execution UUID returns 404."""
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    resp = await client.post(
        f"/api/v1/executions/{uuid4()}/rollback-assessments",
        json={"idempotency_key": "missing-exec-key-01"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_assess_success_lifecycle(test_context):
    """Verify full authorized API lifecycle for rollback readiness assessment."""
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}

    # 1. Create Assessment (201 Created)
    resp = await client.post(
        f"/api/v1/executions/{execution.id}/rollback-assessments",
        json={"idempotency_key": "api-lifecycle-key-01"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assessment_id = data["id"]
    assert data["readiness_status"] == "not_applicable"
    assert data["applicability"] == "not_applicable"
    assert data["risk_level"] == "low"
    assert data["human_authorization_required"] is True
    assert data["rollback_execution_enabled"] is False
    assert data["system_changes_performed"] is False
    assert data["is_replay"] is False

    # 2. Idempotent Replay (200 OK)
    replay_resp = await client.post(
        f"/api/v1/executions/{execution.id}/rollback-assessments",
        json={"idempotency_key": "api-lifecycle-key-01"},
        headers=headers,
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["is_replay"] is True

    # 3. Retrieve Details
    detail_resp = await client.get(
        f"/api/v1/rollback-assessments/{assessment_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == assessment_id

    # 4. Retrieve Events
    events_resp = await client.get(
        f"/api/v1/rollback-assessments/{assessment_id}/events",
        headers=headers,
    )
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) == 2

    # 5. List Assessments
    list_resp = await client.get(
        f"/api/v1/rollback-assessments?execution_id={execution.id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_api_no_rollback_execution_endpoint_exists(test_context):
    """Verify that NO rollback execution endpoint exists in the platform."""
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}

    # Attempt POST to hypothetical execution endpoints
    hypothetical_endpoints = [
        f"/api/v1/executions/{uuid4()}/rollback",
        f"/api/v1/executions/{uuid4()}/rollback/execute",
        f"/api/v1/rollback-assessments/{uuid4()}/execute",
    ]
    for url in hypothetical_endpoints:
        resp = await client.post(url, headers=headers)
        assert resp.status_code in (404, 405), f"Endpoint '{url}' must not exist!"
