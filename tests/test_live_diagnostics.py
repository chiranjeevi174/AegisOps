import inspect
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from aegisops.core.config import get_settings
from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.execution import (
    ExecutionMode,
    ExecutionStatus,
    RemediationExecution,
)
from aegisops.domain.execution_event import ExecutionEventType
from aegisops.domain.incident import Incident
from aegisops.execution.diagnostics import execute_diagnostic_operation
from aegisops.execution.registry import (
    OperationNotAllowedError,
    validate_operation_parameters,
)
from aegisops.integrations.prometheus import MetricSample, PrometheusError
from aegisops.services import approvals, executions
from aegisops.services.executions import (
    ConcurrencyConflictError,
    IdempotencyConflictError,
    LiveDiagnosticsDisabledError,
    ScopeValidationError,
    reconcile_stale_executions,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.workflows.remediation import RemediationAction, RemediationPlan

# =========================================================================
# Helpers and Builders
# =========================================================================


@contextmanager
def patch_live_diagnostics(enabled: bool = True):
    settings = get_settings()
    original = settings.live_diagnostics_enabled
    object.__setattr__(settings, "live_diagnostics_enabled", enabled)
    try:
        yield
    finally:
        object.__setattr__(settings, "live_diagnostics_enabled", original)


def build_plan_for_operation(operation_id: str) -> RemediationPlan:
    mapping = {
        "inspect_service_health": (
            "Inspect Service Health and Availability",
            "diagnostic",
            "Service uptime and endpoint inspection.",
        ),
        "inspect_cpu_metrics": (
            "Inspect CPU Utilization Trends",
            "diagnostic",
            "CPU contention, core allocation, and throttling telemetry.",
        ),
        "inspect_latency_metrics": (
            "Inspect API Response Latency",
            "diagnostic",
            "Latency distributions and response duration curves.",
        ),
        "inspect_error_rate": (
            "Inspect HTTP 5xx Error Rate",
            "diagnostic",
            "HTTP failure spikes and error percentage ratios.",
        ),
        "review_service_configuration": (
            "Review Service Configuration Flags",
            "configuration_review",
            "JVM memory and thread pool settings audit.",
        ),
    }
    title, action_type, description = mapping.get(
        operation_id, ("Inspect Diagnostic Metrics", "diagnostic", "Metrics audit.")
    )

    return RemediationPlan(
        incident_summary="Synthetic diagnostic inspection incident.",
        planning_basis="RCA findings requiring telemetry verification.",
        recommended_actions=[
            RemediationAction(
                title=title,
                description=description,
                rationale="Required for verification.",
                supporting_evidence=["Observed degradation"],
                prerequisites=["Monitoring access"],
                risk_level="low",  # pyright: ignore[reportArgumentType]
                action_type=action_type,  # pyright: ignore[reportArgumentType]
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


async def create_test_incident(session_factory) -> Incident:
    incident_id = uuid4()
    async with session_factory() as session:
        incident = Incident(
            id=incident_id,
            title="Production Service Degradation",
            description="Elevated latency and CPU contention observed.",
            severity="high",
            status="open",
            source="alertmanager",
            alert_fingerprint=f"fp-diag-{incident_id}",
            alert_started_at=datetime.now(UTC),
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
    return incident


async def create_approved_plan(
    session_factory,
    incident_id,
    operation_id: str = "inspect_cpu_metrics",
    decided_at: datetime | None = None,
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
        approval.decided_at = decided_at or now
        approval.decision_reason = "Approved for read-only diagnostics"
        await session.commit()
        await session.refresh(approval)
    return approval


# =========================================================================
# 1. Security Hardening Tests
# =========================================================================


def test_no_credentials_hardcoded_in_auth_module():
    import aegisops.core.auth as auth_mod

    source = inspect.getsource(auth_mod)
    assert "DEFAULT_DEV_ACTORS" not in source
    assert "aegisops-dev-operator-token" not in source
    assert "aegisops-dev-approver-token" not in source


@pytest.mark.asyncio
async def test_auth_operator_permission_enforcement(test_context):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    # 1. Unauthenticated request rejected
    res_unauth = await client.post(
        "/api/v1/executions/diagnose",
        json={
            "approval_id": str(approval.id),
            "incident_id": str(incident.id),
            "operation_id": "inspect_cpu_metrics",
            "recommendation_index": 1,
            "idempotency_key": "unauth-key",
        },
    )
    assert res_unauth.status_code == 401

    # 2. Invalid token rejected
    res_invalid = await client.post(
        "/api/v1/executions/diagnose",
        headers={"Authorization": "Bearer invalid-token-xyz"},
        json={
            "approval_id": str(approval.id),
            "incident_id": str(incident.id),
            "operation_id": "inspect_cpu_metrics",
            "recommendation_index": 1,
            "idempotency_key": "invalid-token-key",
        },
    )
    assert res_invalid.status_code == 401

    # 3. Viewer token lacks executor role -> 403 Forbidden
    res_viewer = await client.post(
        "/api/v1/executions/diagnose",
        headers={"Authorization": "Bearer aegisops-dev-viewer-token"},
        json={
            "approval_id": str(approval.id),
            "incident_id": str(incident.id),
            "operation_id": "inspect_cpu_metrics",
            "recommendation_index": 1,
            "idempotency_key": "viewer-key",
        },
    )
    assert res_viewer.status_code == 403
    assert "lacks execution permission" in res_viewer.json()["detail"]


@pytest.mark.asyncio
async def test_audit_retention_foreign_key_protection(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )
    approval_id = approval.id
    incident_id = incident.id

    async with session_factory() as session:
        # 1. Verify approval cannot be deleted when it has approval_events
        appr_obj = await session.get(RemediationApproval, approval_id)
        assert appr_obj is not None
        events = await approvals.get_approval_events(session, approval_id)
        assert len(events) >= 1

        with pytest.raises(IntegrityError):
            await session.delete(appr_obj)
            await session.commit()
        await session.rollback()

    # 2. Verify execution cannot be deleted when it has execution_events
    with (
        patch_live_diagnostics(True),
        patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range,
    ):
        mock_range.return_value = [
            MetricSample(timestamp=datetime.now(UTC), value=45.2)
        ]
        async with session_factory() as session:
            exec_record, _ = await executions.execute_live_diagnostic(
                session=session,
                approval_id=approval_id,
                incident_id=incident_id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters={"window_minutes": 15, "step": "15s"},
                idempotency_key="retention-test-key",
                requested_by="sre-operator-dan",
            )

            # Attempting to delete the execution record must fail closed due to ON DELETE RESTRICT
            with pytest.raises(IntegrityError):
                await session.delete(exec_record)
                await session.commit()
            await session.rollback()


@pytest.mark.asyncio
async def test_recommendation_binding_rejects_cross_domain_operations(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    # Plan is strictly scoped to CPU metrics
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    with patch_live_diagnostics(True):
        async with session_factory() as session:
            # Latency operation attempted against CPU-scoped recommendation
            with pytest.raises(
                ScopeValidationError, match="outside the authorized scope"
            ):
                await executions.validate_approval_eligibility(
                    session=session,
                    approval_id=approval.id,
                    incident_id=incident.id,
                    operation_id="inspect_latency_metrics",
                    recommendation_index=1,
                    actor_identity="sre-operator-dan",
                    mode=ExecutionMode.LIVE_DIAGNOSTIC,
                )


@pytest.mark.asyncio
async def test_tampered_plan_hash_rejected_in_live_diagnostics(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    # Tamper with plan hash in DB
    async with session_factory() as session:
        appr = await session.get(RemediationApproval, approval.id)
        assert appr is not None
        appr.plan_hash = "f" * 64
        await session.commit()

    with patch_live_diagnostics(True):
        async with session_factory() as session:
            with pytest.raises(PlanIntegrityError):
                await executions.validate_approval_eligibility(
                    session=session,
                    approval_id=approval.id,
                    incident_id=incident.id,
                    operation_id="inspect_cpu_metrics",
                    recommendation_index=1,
                    actor_identity="sre-operator-dan",
                    mode=ExecutionMode.LIVE_DIAGNOSTIC,
                )


# =========================================================================
# 2. Live Diagnostics Handlers & Error Handling
# =========================================================================


def test_live_diagnostics_service_health_success():
    with patch("aegisops.execution.diagnostics.query_prometheus") as mock_query:
        mock_query.return_value = 1.0

        res = execute_diagnostic_operation(
            "inspect_service_health",
            {"service_name": "checkout-service", "include_dependencies": True},
        )

        assert res.operation_id == "inspect_service_health"
        assert res.execution_mode == "live_diagnostic"
        assert res.actual_infrastructure_access is True
        assert res.system_changes_performed is False
        assert res.data_availability_status == "available"
        assert res.summary is not None
        assert res.summary.latest_value == 1.0
        assert res.summary.unit == "binary"
        assert len(res.measurements) == 1
        assert res.measurements[0]["status"] == "UP"


def test_live_diagnostics_cpu_metrics_success():
    now = datetime.now(UTC)
    samples = [
        MetricSample(timestamp=now - timedelta(minutes=2), value=32.5),
        MetricSample(timestamp=now - timedelta(minutes=1), value=78.2),
        MetricSample(timestamp=now, value=65.0),
    ]

    with patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range:
        mock_range.return_value = samples

        res = execute_diagnostic_operation(
            "inspect_cpu_metrics",
            {"window_minutes": 15, "step": "15s"},
        )

        assert res.operation_id == "inspect_cpu_metrics"
        assert res.data_availability_status == "available"
        assert res.summary is not None
        assert res.summary.sample_count == 3
        assert res.summary.min_value == 32.5
        assert res.summary.max_value == 78.2
        assert res.summary.latest_value == 65.0
        assert res.summary.unit == "%"


def test_live_diagnostics_latency_metrics_success():
    now = datetime.now(UTC)
    samples = [
        MetricSample(timestamp=now - timedelta(minutes=1), value=0.125),
        MetricSample(timestamp=now, value=0.450),
    ]

    with patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range:
        mock_range.return_value = samples

        res = execute_diagnostic_operation(
            "inspect_latency_metrics",
            {"window_minutes": 10, "step": "15s"},
        )

        assert res.operation_id == "inspect_latency_metrics"
        assert res.summary is not None
        assert res.summary.latest_value == 0.45
        assert res.summary.unit == "s"


def test_live_diagnostics_error_rate_success():
    now = datetime.now(UTC)
    samples = [
        MetricSample(timestamp=now - timedelta(minutes=1), value=0.002),
        MetricSample(timestamp=now, value=0.015),
    ]

    with patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range:
        mock_range.return_value = samples

        res = execute_diagnostic_operation(
            "inspect_error_rate",
            {"window_minutes": 5, "step": "15s"},
        )

        assert res.operation_id == "inspect_error_rate"
        assert res.summary is not None
        assert res.summary.unit == "ratio"
        assert res.summary.latest_value == 0.015


def test_live_diagnostics_missing_metric_handled_safely():
    with patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range:
        mock_range.return_value = []

        res = execute_diagnostic_operation(
            "inspect_cpu_metrics",
            {"window_minutes": 15, "step": "15s"},
        )

        assert res.data_availability_status == "no_data"
        assert res.summary is None
        assert len(res.measurements) == 0
        assert res.actual_infrastructure_access is True


def test_live_diagnostics_prometheus_http_failure():
    with patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range:
        mock_range.side_effect = PrometheusError("Connection refused by Prometheus")

        with pytest.raises(PrometheusError, match="Connection refused"):
            execute_diagnostic_operation(
                "inspect_cpu_metrics",
                {"window_minutes": 15, "step": "15s"},
            )


def test_live_diagnostics_rejects_unsupported_operations():
    # review_service_configuration is simulation-only
    with pytest.raises(
        OperationNotAllowedError, match="does not support live diagnostics"
    ):
        execute_diagnostic_operation(
            "review_service_configuration",
            {"component": "jvm"},
        )

    # Unknown operations rejected
    with pytest.raises(OperationNotAllowedError):
        execute_diagnostic_operation("arbitrary_command", {})


def test_live_diagnostics_excessive_window_rejected():
    with pytest.raises(ValidationError):
        validate_operation_parameters(
            "inspect_cpu_metrics",
            {"window_minutes": 180},  # Max allowed is 120
        )


# =========================================================================
# 3. Execution Service Persistence & Concurrency
# =========================================================================


@pytest.mark.asyncio
async def test_live_diagnostics_disabled_by_default(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    # Setting is False by default
    with patch_live_diagnostics(False):
        async with session_factory() as session:
            with pytest.raises(LiveDiagnosticsDisabledError, match="disabled"):
                await executions.execute_live_diagnostic(
                    session=session,
                    approval_id=approval.id,
                    incident_id=incident.id,
                    operation_id="inspect_cpu_metrics",
                    recommendation_index=1,
                    parameters={"window_minutes": 15, "step": "15s"},
                    idempotency_key="disabled-key-1",
                    requested_by="sre-operator-dan",
                )


@pytest.mark.asyncio
async def test_simulation_remains_available_when_live_diagnostics_disabled(
    test_context,
):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    with patch_live_diagnostics(False):
        async with session_factory() as session:
            rec, is_replay = await executions.execute_simulation(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters={"window_minutes": 15, "step": "15s"},
                idempotency_key="sim-still-works",
                requested_by="sre-operator-dan",
            )
            assert is_replay is False
            assert rec.mode == ExecutionMode.SIMULATION.value
            assert rec.status == ExecutionStatus.SIMULATED.value


@pytest.mark.asyncio
async def test_live_diagnostic_execution_persistence_and_audit(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    with (
        patch_live_diagnostics(True),
        patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range,
    ):
        mock_range.return_value = [
            MetricSample(timestamp=datetime.now(UTC), value=55.5)
        ]
        async with session_factory() as session:
            record, is_replay = await executions.execute_live_diagnostic(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters={"window_minutes": 15, "step": "15s"},
                idempotency_key="live-diag-001",
                requested_by="sre-operator-dan",
            )

            assert is_replay is False
            assert record.mode == ExecutionMode.LIVE_DIAGNOSTIC.value
            assert record.status == ExecutionStatus.DIAGNOSED.value
            assert record.diagnostic_result is not None
            assert record.diagnostic_result["data_availability_status"] == "available"
            assert record.simulation_result is None

            # Verify audit events
            events = await executions.get_execution_events(session, record.id)
            assert len(events) == 2
            assert events[0].event_type == ExecutionEventType.DIAGNOSTIC_STARTED.value
            assert events[1].event_type == ExecutionEventType.DIAGNOSTIC_COMPLETED.value
            assert events[1].details["actual_infrastructure_access"] is True
            assert events[1].details["system_changes_performed"] is False


@pytest.mark.asyncio
async def test_live_diagnostic_idempotent_replay(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    params = {"window_minutes": 15, "step": "15s"}

    with (
        patch_live_diagnostics(True),
        patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range,
    ):
        mock_range.return_value = [
            MetricSample(timestamp=datetime.now(UTC), value=60.0)
        ]
        async with session_factory() as session:
            first_record, is_replay_1 = await executions.execute_live_diagnostic(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters=params,
                idempotency_key="live-replay-key",
                requested_by="sre-operator-dan",
            )
            assert is_replay_1 is False

            # Replay must return existing record without new query
            second_record, is_replay_2 = await executions.execute_live_diagnostic(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters=params,
                idempotency_key="live-replay-key",
                requested_by="sre-operator-dan",
            )
            assert is_replay_2 is True
            assert first_record.id == second_record.id


@pytest.mark.asyncio
async def test_live_diagnostic_idempotency_conflict_mode_or_params(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    with (
        patch_live_diagnostics(True),
        patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range,
    ):
        mock_range.return_value = [
            MetricSample(timestamp=datetime.now(UTC), value=60.0)
        ]
        async with session_factory() as session:
            await executions.execute_live_diagnostic(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters={"window_minutes": 15, "step": "15s"},
                idempotency_key="conflict-key-diag",
                requested_by="sre-operator-dan",
            )

            # Conflicting window_minutes parameter
            with pytest.raises(IdempotencyConflictError):
                await executions.execute_live_diagnostic(
                    session=session,
                    approval_id=approval.id,
                    incident_id=incident.id,
                    operation_id="inspect_cpu_metrics",
                    recommendation_index=1,
                    parameters={"window_minutes": 30, "step": "15s"},
                    idempotency_key="conflict-key-diag",
                    requested_by="sre-operator-dan",
                )


@pytest.mark.asyncio
async def test_live_diagnostic_concurrency_lock_protection(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    async with session_factory() as session:
        # Simulate a currently RUNNING diagnostic execution
        running_exec = RemediationExecution(
            incident_id=incident.id,
            approval_id=approval.id,
            approved_plan_hash=approval.plan_hash,
            approved_plan_version=approval.version,
            selected_recommendation_index=1,
            selected_recommendation_title="Inspect CPU Utilization",
            operation_id="inspect_cpu_metrics",
            parameters={"window_minutes": 15, "step": "15s"},
            requested_by="sre-operator-dan",
            mode=ExecutionMode.LIVE_DIAGNOSTIC.value,
            status=ExecutionStatus.RUNNING.value,
            idempotency_key="in-flight-key",
            requested_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_ms=0,
        )
        session.add(running_exec)
        await session.commit()

    with patch_live_diagnostics(True):
        async with session_factory() as session:
            with pytest.raises(ConcurrencyConflictError, match="already in progress"):
                await executions.execute_live_diagnostic(
                    session=session,
                    approval_id=approval.id,
                    incident_id=incident.id,
                    operation_id="inspect_cpu_metrics",
                    recommendation_index=1,
                    parameters={"window_minutes": 15, "step": "15s"},
                    idempotency_key="in-flight-key",
                    requested_by="sre-operator-dan",
                )


@pytest.mark.asyncio
async def test_worker_interruption_recovery_policy(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    # Insert an abandoned execution started 10 minutes ago
    stale_time = datetime.now(UTC) - timedelta(minutes=10)
    async with session_factory() as session:
        stale_exec = RemediationExecution(
            incident_id=incident.id,
            approval_id=approval.id,
            approved_plan_hash=approval.plan_hash,
            approved_plan_version=approval.version,
            selected_recommendation_index=1,
            selected_recommendation_title="Inspect CPU Utilization",
            operation_id="inspect_cpu_metrics",
            parameters={"window_minutes": 15, "step": "15s"},
            requested_by="sre-operator-dan",
            mode=ExecutionMode.LIVE_DIAGNOSTIC.value,
            status=ExecutionStatus.RUNNING.value,
            idempotency_key="crashed-worker-key",
            requested_at=stale_time,
            started_at=stale_time,
            completed_at=stale_time,
            duration_ms=0,
        )
        session.add(stale_exec)
        await session.commit()
        stale_id = stale_exec.id

    async with session_factory() as session:
        reconciled = await reconcile_stale_executions(session, threshold_minutes=5)
        assert reconciled == 1

        reloaded = await session.get(RemediationExecution, stale_id)
        assert reloaded is not None
        assert reloaded.status == ExecutionStatus.TIMED_OUT.value


# =========================================================================
# 4. Safety Regression Tests
# =========================================================================


@pytest.mark.asyncio
async def test_live_diagnostics_never_mutates_infrastructure_or_incident_status(
    test_context,
):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_approved_plan(
        session_factory, incident.id, "inspect_cpu_metrics"
    )

    with (
        patch_live_diagnostics(True),
        patch("aegisops.execution.diagnostics.query_prometheus_range") as mock_range,
    ):
        mock_range.return_value = [
            MetricSample(timestamp=datetime.now(UTC), value=42.0)
        ]
        async with session_factory() as session:
            rec, _ = await executions.execute_live_diagnostic(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id="inspect_cpu_metrics",
                recommendation_index=1,
                parameters={"window_minutes": 15, "step": "15s"},
                idempotency_key="safety-check-key",
                requested_by="sre-operator-dan",
            )

            # Live result indicators
            assert rec.diagnostic_result is not None
            assert rec.diagnostic_result["actual_infrastructure_access"] is True
            assert rec.diagnostic_result["system_changes_performed"] is False

            # Incident status MUST strictly remain 'open'
            reloaded_inc = await session.get(Incident, incident.id)
            assert reloaded_inc is not None
            assert reloaded_inc.status == "open"

            # Approval status MUST strictly remain 'approved'
            reloaded_appr = await session.get(RemediationApproval, approval.id)
            assert reloaded_appr is not None
            assert reloaded_appr.status == ApprovalStatus.APPROVED.value
