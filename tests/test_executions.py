import inspect
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.execution import (
    ExecutionMode,
    ExecutionStatus,
)
from aegisops.domain.execution_event import ExecutionEventType
from aegisops.domain.incident import Incident
from aegisops.execution.registry import (
    ALLOWLISTED_OPERATIONS,
    BANNED_OPERATION_NAMES,
    OperationNotAllowedError,
    get_operation_definition,
    validate_operation_parameters,
)
from aegisops.execution.simulator import simulate_operation
from aegisops.services import approvals, executions
from aegisops.services.executions import (
    ApprovalEligibilityError,
    ExecutionExpiredError,
    IdempotencyConflictError,
    ScopeValidationError,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.workflows import incident as incident_workflow
from aegisops.workflows.remediation import RemediationAction, RemediationPlan

# =========================================================================
# Helper Fixtures & Builders
# =========================================================================


def sample_valid_plan(
    title: str = "Inspect Service Health and Availability",
    action_type: str = "diagnostic",
    risk_level: str = "low",
) -> RemediationPlan:
    return RemediationPlan(
        incident_summary="Periodic high latency observed with CPU contention.",
        planning_basis="RCA medium confidence hypothesis on GC pauses.",
        recommended_actions=[
            RemediationAction(
                title=title,
                description=f"Inspect system status and telemetry signals for {title}.",
                rationale="Required for operational health and telemetry verification.",
                supporting_evidence=["Historical latency reached 4.2s"],
                prerequisites=["Access to monitoring metrics"],
                risk_level=risk_level,  # pyright: ignore[reportArgumentType]
                action_type=action_type,  # pyright: ignore[reportArgumentType]
                validation_steps=["Verify telemetry signals and metrics"],
                rollback_considerations=["No rollback required for diagnostic review"],
                requires_human_approval=True,
            )
        ],
        missing_information=["Thread dumps", "GC log files"],
        overall_risk="low",
        requires_human_approval=True,
        execution_enabled=False,
    )


async def create_test_incident(session_factory) -> Incident:
    incident_id = uuid4()
    async with session_factory() as session:
        incident = Incident(
            id=incident_id,
            title="High API latency detected",
            description="API latency spike detected by Alertmanager.",
            severity="high",
            status="open",
            source="alertmanager",
            alert_fingerprint=f"fp-{incident_id}",
            alert_started_at=datetime.now(UTC),
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
    return incident


async def create_test_approval(
    session_factory,
    incident_id,
    status: str = ApprovalStatus.APPROVED.value,
    plan: RemediationPlan | None = None,
    requested_by: str = "sre-engineer-alice",
    decided_by: str = "sre-lead-charlie",
    validity_minutes: int = 120,
    decided_at: datetime | None = None,
) -> RemediationApproval:
    plan = plan or sample_valid_plan()
    now = datetime.now(UTC)
    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident_id,
            plan=plan,
            requested_by=requested_by,
            validity_minutes=validity_minutes,
        )
        if status == ApprovalStatus.APPROVED.value:
            approval.status = ApprovalStatus.APPROVED.value
            approval.decided_by = decided_by
            approval.decided_at = decided_at or now
            approval.decision_reason = "Approved for simulation"
        elif status == ApprovalStatus.REJECTED.value:
            approval.status = ApprovalStatus.REJECTED.value
            approval.decided_by = decided_by
            approval.decided_at = decided_at or now
            approval.decision_reason = "Rejected"
        elif status == ApprovalStatus.SUPERSEDED.value:
            approval.status = ApprovalStatus.SUPERSEDED.value
            approval.decided_by = decided_by
            approval.decided_at = decided_at or now
            approval.decision_reason = "Superseded by newer plan"
        await session.commit()
        await session.refresh(approval)
    return approval


# =========================================================================
# 1. Registry & Allowlist Tests
# =========================================================================


def test_registry_contains_expected_operations():
    expected_ops = {
        "inspect_service_health",
        "inspect_cpu_metrics",
        "inspect_latency_metrics",
        "inspect_error_rate",
        "review_service_configuration",
    }
    assert set(ALLOWLISTED_OPERATIONS.keys()) == expected_ops


def test_registry_real_execution_disabled_for_all_operations():
    for op_id, op_def in ALLOWLISTED_OPERATIONS.items():
        assert op_def.real_execution_supported is False, (
            f"Operation {op_id} must have real_execution_supported=False"
        )
        assert op_def.is_read_only is True
        assert op_def.risk_level == "low"
        assert op_def.required_permission == "execute:diagnostic"
        if op_id == "review_service_configuration":
            assert op_def.live_diagnostic_supported is False
            assert "simulation" in op_def.supported_modes
            assert "live_diagnostic" not in op_def.supported_modes
        else:
            assert op_def.live_diagnostic_supported is True
            assert "live_diagnostic" in op_def.supported_modes


def test_registry_unknown_operation_rejected():
    with pytest.raises(
        OperationNotAllowedError, match="not in the remediation allowlist"
    ):
        get_operation_definition("execute_arbitrary_script")


def test_registry_banned_operations_rejected():
    for banned in BANNED_OPERATION_NAMES:
        with pytest.raises(OperationNotAllowedError):
            get_operation_definition(banned)


def test_registry_parameter_validation_success():
    params = {"service_name": "checkout-service", "include_dependencies": False}
    validated = validate_operation_parameters("inspect_service_health", params)
    assert validated["service_name"] == "checkout-service"
    assert validated["include_dependencies"] is False


def test_registry_parameter_validation_invalid():
    # Length exceeds 50
    with pytest.raises(ValidationError):
        validate_operation_parameters(
            "inspect_service_health", {"service_name": "a" * 51}
        )

    # Invalid window_minutes (< 1)
    with pytest.raises(ValidationError):
        validate_operation_parameters(
            "inspect_cpu_metrics",
            {"window_minutes": 0},
        )


# =========================================================================
# 2. Simulation Engine Tests
# =========================================================================


def test_simulate_operation_deterministic_and_dry_run():
    for op_id in ALLOWLISTED_OPERATIONS:
        params = {}
        if op_id == "inspect_service_health":
            params = {"service_name": "order-service", "include_dependencies": True}
        elif op_id in (
            "inspect_cpu_metrics",
            "inspect_latency_metrics",
            "inspect_error_rate",
        ):
            params = {"window_minutes": 15, "step": "15s"}
        elif op_id == "review_service_configuration":
            params = {"component": "jvm"}

        res = simulate_operation(op_id, params)

        # Non-negotiable simulation invariants
        assert res.operation_id == op_id
        assert res.mode == "simulation"
        assert res.dry_run is True
        assert res.actual_infrastructure_access is False
        assert res.system_changes_performed is False
        assert res.status == "simulated_success"
        assert len(res.expected_observations) > 0


def test_simulate_unknown_operation_fails():
    with pytest.raises(OperationNotAllowedError):
        simulate_operation("shell_command", {})


# =========================================================================
# 3. Approval Eligibility Gate Tests
# =========================================================================


@pytest.mark.asyncio
async def test_eligibility_gate_approved_plan_passes(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    async with session_factory() as session:
        appr, title = await executions.validate_approval_eligibility(
            session=session,
            approval_id=approval.id,
            incident_id=incident.id,
            operation_id="inspect_service_health",
            recommendation_index=1,
            actor_identity="sre-operator-dan",
        )
        assert appr.id == approval.id
        assert "Inspect Service Health" in title


@pytest.mark.asyncio
async def test_eligibility_gate_pending_approval_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(
        session_factory, incident.id, status=ApprovalStatus.PENDING.value
    )

    async with session_factory() as session:
        with pytest.raises(ApprovalEligibilityError, match="must be 'approved'"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_eligibility_gate_rejected_approval_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(
        session_factory, incident.id, status=ApprovalStatus.REJECTED.value
    )

    async with session_factory() as session:
        with pytest.raises(ApprovalEligibilityError, match="must be 'approved'"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_eligibility_gate_superseded_approval_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(
        session_factory, incident.id, status=ApprovalStatus.SUPERSEDED.value
    )

    async with session_factory() as session:
        with pytest.raises(ApprovalEligibilityError, match="must be 'approved'"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_eligibility_gate_expired_execution_window_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    # Decided 125 minutes ago (eligibility window is 120 minutes)
    expired_time = datetime.now(UTC) - timedelta(minutes=125)
    approval = await create_test_approval(
        session_factory, incident.id, decided_at=expired_time
    )

    async with session_factory() as session:
        with pytest.raises(
            ExecutionExpiredError, match="Execution authorization window expired"
        ):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )

        # Verify approval itself was NOT modified to expired status (remains approved in DB)
        reloaded = await session.get(RemediationApproval, approval.id)
        assert reloaded is not None
        assert reloaded.status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_eligibility_gate_incident_mismatch_rejected(test_context):
    _, session_factory = test_context
    incident_a = await create_test_incident(session_factory)
    incident_b = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident_a.id)

    async with session_factory() as session:
        with pytest.raises(ApprovalEligibilityError, match="belongs to incident"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident_b.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_eligibility_gate_tampered_plan_hash_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    # Tamper with snapshot in database
    async with session_factory() as session:
        appr = await session.get(RemediationApproval, approval.id)
        assert appr is not None
        tampered_snapshot = dict(appr.plan_snapshot)
        tampered_snapshot["incident_summary"] = "Tampered summary to evade controls"
        appr.plan_snapshot = tampered_snapshot
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(PlanIntegrityError, match="integrity verification failed"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_eligibility_gate_recommendation_index_out_of_bounds(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    async with session_factory() as session:
        with pytest.raises(ScopeValidationError, match="out of bounds"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=99,
                actor_identity="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_eligibility_gate_mismatched_recommendation_binding_rejected(
    test_context,
):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    # 1. Action type mismatch: configuration_review vs diagnostic operation
    config_plan = sample_valid_plan(
        title="Review JVM Configuration Flags",
        action_type="configuration_review",
    )
    approval_config = await create_test_approval(
        session_factory, incident.id, plan=config_plan
    )

    async with session_factory() as session:
        with pytest.raises(
            ScopeValidationError, match="requires recommendation action_type"
        ):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval_config.id,
                incident_id=incident.id,
                operation_id="inspect_service_health",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )

    # 2. Domain scope mismatch: latency diagnostic vs CPU operation
    latency_plan = sample_valid_plan(
        title="Inspect Latency Response Metrics",
        action_type="diagnostic",
    )
    approval_latency = await create_test_approval(
        session_factory, incident.id, plan=latency_plan
    )

    async with session_factory() as session:
        with pytest.raises(ScopeValidationError, match="outside the authorized scope"):
            await executions.validate_approval_eligibility(
                session=session,
                approval_id=approval_latency.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                actor_identity="sre-operator-dan",
            )


# =========================================================================
# 4. Persistence & Idempotency Tests
# =========================================================================


@pytest.mark.asyncio
async def test_execute_simulation_success_and_audit_event(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(
        session_factory,
        incident.id,
        plan=sample_valid_plan(
            title="Inspect Latency Metrics", action_type="diagnostic"
        ),
    )

    async with session_factory() as session:
        exec_record, is_replay = await executions.execute_simulation(
            session=session,
            approval_id=approval.id,
            incident_id=incident.id,
            operation_id="inspect_latency_metrics",
            recommendation_index=1,
            parameters={"window_minutes": 15, "step": "15s"},
            idempotency_key="test-key-001",
            requested_by="sre-operator-dan",
        )

        assert is_replay is False
        assert exec_record.id is not None
        assert exec_record.mode == ExecutionMode.SIMULATION.value
        assert exec_record.status == ExecutionStatus.SIMULATED.value
        assert exec_record.idempotency_key == "test-key-001"
        assert exec_record.simulation_result is not None
        assert exec_record.simulation_result["dry_run"] is True

        # Verify audit event was persisted
        events = await executions.get_execution_events(session, exec_record.id)
        assert len(events) == 1
        assert events[0].event_type == ExecutionEventType.SIMULATION_COMPLETED.value
        assert events[0].actor == "sre-operator-dan"
        assert events[0].details["idempotency_key"] == "test-key-001"
        assert events[0].details["actual_infrastructure_access"] is False


@pytest.mark.asyncio
async def test_execute_simulation_idempotent_replay(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(
        session_factory,
        incident.id,
        plan=sample_valid_plan(
            title="Inspect Latency Metrics", action_type="diagnostic"
        ),
    )

    params = {"window_minutes": 15, "step": "15s"}

    async with session_factory() as session:
        # 1. First execution
        first_record, is_replay = await executions.execute_simulation(
            session=session,
            approval_id=approval.id,
            incident_id=incident.id,
            operation_id="inspect_latency_metrics",
            recommendation_index=1,
            parameters=params,
            idempotency_key="idempotent-key-100",
            requested_by="sre-operator-dan",
        )
        assert is_replay is False

        # 2. Replay with identical key & parameters
        second_record, is_replay_2 = await executions.execute_simulation(
            session=session,
            approval_id=approval.id,
            incident_id=incident.id,
            operation_id="inspect_latency_metrics",
            recommendation_index=1,
            parameters=params,
            idempotency_key="idempotent-key-100",
            requested_by="sre-operator-dan",
        )
        assert is_replay_2 is True
        assert first_record.id == second_record.id
        assert second_record.status == ExecutionStatus.SIMULATED.value

        # Only 1 audit event should exist (no duplicate audit event created on replay)
        events = await executions.get_execution_events(session, first_record.id)
        assert len(events) == 1


@pytest.mark.asyncio
async def test_execute_simulation_idempotency_conflict_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(
        session_factory,
        incident.id,
        plan=sample_valid_plan(
            title="Inspect Latency Metrics", action_type="diagnostic"
        ),
    )

    async with session_factory() as session:
        # First call with window_minutes 15
        await executions.execute_simulation(
            session=session,
            approval_id=approval.id,
            incident_id=incident.id,
            operation_id="inspect_latency_metrics",
            recommendation_index=1,
            parameters={"window_minutes": 15, "step": "15s"},
            idempotency_key="conflict-key-999",
            requested_by="sre-operator-dan",
        )

        # Second call with conflicting window_minutes 60
        with pytest.raises(IdempotencyConflictError, match="conflicting.*parameters"):
            await executions.execute_simulation(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_latency_metrics",
                recommendation_index=1,
                parameters={"window_minutes": 60, "step": "15s"},
                idempotency_key="conflict-key-999",
                requested_by="sre-operator-dan",
            )


# =========================================================================
# 5. API Endpoints & Authentication Tests
# =========================================================================


@pytest.mark.asyncio
async def test_api_list_operations_unauthenticated(test_context):
    client, _ = test_context
    res = await client.get("/api/v1/execution-operations")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_api_list_operations_authenticated(test_context):
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-viewer-token"}
    res = await client.get("/api/v1/execution-operations", headers=headers)
    assert res.status_code == 200
    ops = res.json()
    assert len(ops) == 5
    for op in ops:
        assert op["real_execution_supported"] is False


@pytest.mark.asyncio
async def test_api_simulate_unauthorized_role(test_context):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    # Viewer token lacks executor permission
    viewer_headers = {"Authorization": "Bearer aegisops-dev-viewer-token"}
    payload = {
        "approval_id": str(approval.id),
        "incident_id": str(incident.id),
        "operation_id": "inspect_service_health",
        "recommendation_index": 1,
        "parameters": {"service_name": "checkout"},
        "idempotency_key": "viewer-test-key",
    }
    res = await client.post(
        "/api/v1/executions/simulate", headers=viewer_headers, json=payload
    )
    assert res.status_code == 403
    assert "lacks execution permission" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_simulate_success_with_operator_token(test_context):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    operator_headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    payload = {
        "approval_id": str(approval.id),
        "incident_id": str(incident.id),
        "operation_id": "inspect_service_health",
        "recommendation_index": 1,
        "parameters": {"service_name": "checkout"},
        "idempotency_key": "operator-test-key-01",
    }
    res = await client.post(
        "/api/v1/executions/simulate", headers=operator_headers, json=payload
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "simulation"
    assert data["status"] == "simulated"
    assert data["is_replay"] is False
    assert data["actual_infrastructure_access"] is False
    assert data["system_changes_performed"] is False
    assert data["simulation_result"]["dry_run"] is True
    execution_id = data["id"]

    # Test replay over API returns 200 OK
    res_replay = await client.post(
        "/api/v1/executions/simulate", headers=operator_headers, json=payload
    )
    assert res_replay.status_code == 200
    data_replay = res_replay.json()
    assert data_replay["id"] == execution_id
    assert data_replay["is_replay"] is True

    # Test GET execution details
    get_res = await client.get(
        f"/api/v1/executions/{execution_id}", headers=operator_headers
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == execution_id

    # Test GET execution events
    events_res = await client.get(
        f"/api/v1/executions/{execution_id}/events", headers=operator_headers
    )
    assert events_res.status_code == 200
    assert len(events_res.json()) == 1


@pytest.mark.asyncio
async def test_api_simulate_unknown_operation_rejected(test_context):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    operator_headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    payload = {
        "approval_id": str(approval.id),
        "incident_id": str(incident.id),
        "operation_id": "run_arbitrary_shell_command",
        "recommendation_index": 1,
        "parameters": {"command": "rm -rf /"},
        "idempotency_key": "malicious-cmd-key",
    }
    res = await client.post(
        "/api/v1/executions/simulate", headers=operator_headers, json=payload
    )
    assert res.status_code == 422
    assert "not in the remediation allowlist" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_simulate_missing_approval_returns_409(test_context):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)

    operator_headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    missing_id = str(uuid4())
    payload = {
        "approval_id": missing_id,
        "incident_id": str(incident.id),
        "operation_id": "inspect_service_health",
        "recommendation_index": 1,
        "parameters": {"service_name": "checkout"},
        "idempotency_key": "missing-approval-key",
    }
    res = await client.post(
        "/api/v1/executions/simulate", headers=operator_headers, json=payload
    )
    assert res.status_code == 409
    assert "not found" in res.json()["detail"]


# =========================================================================
# 6. Safety Regression Tests
# =========================================================================


def test_safety_regression_remediation_plan_invariants():
    plan = sample_valid_plan()
    assert plan.execution_enabled is False
    assert plan.requires_human_approval is True

    # Attempting to construct plan with execution_enabled=True must raise ValidationError
    with pytest.raises(ValidationError):
        RemediationPlan(
            incident_summary="Test",
            planning_basis="Test",
            recommended_actions=[],
            missing_information=[],
            overall_risk="low",
            requires_human_approval=True,
            execution_enabled=True,  # Disallowed by model
        )


def test_safety_regression_workflow_has_no_execution_edge():
    # LangGraph workflow inspection
    source = inspect.getsource(incident_workflow)
    assert "execute_simulation" not in source
    assert "simulate_operation" not in source
    assert "RemediationExecution" not in source


@pytest.mark.asyncio
async def test_safety_regression_approval_does_not_mutate_incident_status(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)

    async with session_factory() as session:
        # Run execution simulation
        await executions.execute_simulation(
            session=session,
            approval_id=approval.id,
            incident_id=incident.id,
            operation_id="inspect_service_health",
            recommendation_index=1,
            parameters={"service_name": "checkout"},
            idempotency_key="incident-status-check",
            requested_by="sre-operator-dan",
        )

        # Incident status must strictly remain "open"
        reloaded_incident = await session.get(Incident, incident.id)
        assert reloaded_incident is not None
        assert reloaded_incident.status == "open"

        # Approval status must strictly remain "approved"
        reloaded_approval = await session.get(RemediationApproval, approval.id)
        assert reloaded_approval is not None
        assert reloaded_approval.status == "approved"
