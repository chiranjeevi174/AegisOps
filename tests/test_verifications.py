from datetime import UTC, datetime, timedelta
from unittest.mock import patch
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
from aegisops.domain.verification import (
    ExecutionVerification,
    VerificationOutcome,
    VerificationStatus,
)
from aegisops.domain.verification_event import VerificationEventType
from aegisops.integrations.prometheus import MetricSample, PrometheusError
from aegisops.services import verifications
from aegisops.services.executions import (
    ConcurrencyConflictError,
    IdempotencyConflictError,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.verification.comparison import compare_metric_observations
from aegisops.verification.evidence import (
    retrieve_baseline_evidence,
    retrieve_followup_evidence,
)
from aegisops.verification.schemas import (
    MetricComparisonResult,
    MetricObservation,
    PostExecutionVerificationResult,
    VerificationCriteria,
)
from aegisops.workflows.remediation import RemediationAction, RemediationPlan

# =========================================================================
# Test Helpers and Builders
# =========================================================================


async def create_test_incident(session_factory) -> Incident:
    async with session_factory() as session:
        incident = Incident(
            title="Service latency and health degradation",
            description="High latency and packet drops observed across endpoints.",
            severity="high",
            status="open",
            source="alertmanager",
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
        return incident


from aegisops.services import approvals


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
    }
    title, action_type, description = mapping.get(
        operation_id,
        (
            "Inspect API Response Latency",
            "diagnostic",
            "Latency distributions and response duration curves.",
        ),
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
                risk_level="low",
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
    idempotency_key: str = "exec-test-key-01",
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
                "summary": {"latest_value": 0.25, "mean_value": 0.25},
            }
            if mode == ExecutionMode.LIVE_DIAGNOSTIC
            else None,
            duration_ms=2000,
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        return execution


# =========================================================================
# 1. Schema & Invariant Tests
# =========================================================================


def test_verification_schemas_enforce_remediation_success_false():
    """Verify that remediation_success_confirmed MUST strictly be False."""
    with pytest.raises(ValidationError, match="remediation_success_confirmed"):
        PostExecutionVerificationResult(
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_latency_metrics",
            execution_mode="live_diagnostic",
            outcome=VerificationOutcome.DIAGNOSTIC_VERIFIED,
            criteria=VerificationCriteria(),
            verified_at=datetime.now(UTC),
            human_review_required=True,
            remediation_success_confirmed=True,  # Disallowed
        )


def test_verification_schemas_enforce_human_review_required_true():
    """Verify that human_review_required MUST strictly be True."""
    with pytest.raises(ValidationError, match="human_review_required"):
        PostExecutionVerificationResult(
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_latency_metrics",
            execution_mode="live_diagnostic",
            outcome=VerificationOutcome.DIAGNOSTIC_VERIFIED,
            criteria=VerificationCriteria(),
            verified_at=datetime.now(UTC),
            human_review_required=False,  # Disallowed
            remediation_success_confirmed=False,
        )


def test_verification_schemas_valid_construction():
    """Verify standard valid verification model instantiation."""
    now = datetime.now(UTC)
    result = PostExecutionVerificationResult(
        execution_id=uuid4(),
        incident_id=uuid4(),
        approval_id=uuid4(),
        operation_id="inspect_latency_metrics",
        execution_mode="live_diagnostic",
        outcome=VerificationOutcome.DIAGNOSTIC_VERIFIED,
        criteria=VerificationCriteria(baseline_window_minutes=20),
        limitations=["Simulator scenario caveat"],
        observations=["Latency stable"],
        verified_at=now,
    )
    assert result.outcome == VerificationOutcome.DIAGNOSTIC_VERIFIED
    assert result.remediation_success_confirmed is False
    assert result.human_review_required is True
    assert result.criteria.baseline_window_minutes == 20


# =========================================================================
# 2. Evidence Collection Tests
# =========================================================================


def test_baseline_retrieval_success():
    """Verify that baseline evidence queries Prometheus and labels retrospective samples."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_cpu_metrics",
        started_at=now,
        completed_at=now + timedelta(seconds=2),
    )
    criteria = VerificationCriteria(baseline_window_minutes=15)

    with patch("aegisops.verification.evidence.query_prometheus_range") as mock_range:
        mock_range.return_value = [
            MetricSample(timestamp=now - timedelta(minutes=10), value=40.0),
            MetricSample(timestamp=now - timedelta(minutes=5), value=50.0),
        ]

        obs, limits = retrieve_baseline_evidence(execution, criteria)
        assert obs is not None
        assert obs.is_retrospective is True
        assert obs.label == "retrospectively_retrieved_baseline"
        assert obs.sample_count == 2
        assert obs.mean_value == 45.0
        assert obs.min_value == 40.0
        assert obs.max_value == 50.0
        assert obs.data_availability == "available"
        assert len(limits) == 0


def test_baseline_retrieval_empty_handled():
    """Verify that empty Prometheus query returns no_data observation without crashing."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_cpu_metrics",
        started_at=now,
        completed_at=now + timedelta(seconds=2),
    )
    criteria = VerificationCriteria(baseline_window_minutes=15)

    with patch("aegisops.verification.evidence.query_prometheus_range") as mock_range:
        mock_range.return_value = []

        obs, _ = retrieve_baseline_evidence(execution, criteria)
        assert obs is not None
        assert obs.sample_count == 0
        assert obs.mean_value is None
        assert obs.data_availability == "no_data"


def test_baseline_retrieval_prometheus_error():
    """Verify that Prometheus query errors are recorded as error observations and limitations."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_cpu_metrics",
        started_at=now,
        completed_at=now + timedelta(seconds=2),
    )
    criteria = VerificationCriteria(baseline_window_minutes=15)

    with patch("aegisops.verification.evidence.query_prometheus_range") as mock_range:
        mock_range.side_effect = PrometheusError(
            "Connection timeout to Prometheus:9090"
        )

        obs, limits = retrieve_baseline_evidence(execution, criteria)
        assert obs is not None
        assert obs.data_availability == "error"
        assert len(limits) >= 1
        assert "Connection timeout" in limits[0]


def test_followup_retrieval_insufficient_time_elapsed():
    """Verify that execution completed 0 seconds ago reports insufficient observation time."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_latency_metrics",
        started_at=now,
        completed_at=now,  # Just completed right now
    )
    criteria = VerificationCriteria(followup_window_minutes=15)

    obs, limits = retrieve_followup_evidence(execution, criteria)
    assert obs is not None
    assert obs.data_availability == "insufficient_samples"
    assert any("Insufficient post-execution observation time" in lim for lim in limits)


# =========================================================================
# 3. Deterministic Comparison Tests
# =========================================================================


def test_comparison_numerical_decrease_improved():
    """Verify that lower latency is evaluated as 'improved' with advisory caveat."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria()
    baseline = MetricObservation(
        metric_name="API Response Latency",
        expression="aegisops_sim_latency_seconds",
        unit="s",
        sample_count=4,
        mean_value=2.5,
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    followup = MetricObservation(
        metric_name="API Response Latency",
        expression="aegisops_sim_latency_seconds",
        unit="s",
        sample_count=4,
        mean_value=0.5,
        interval_start=now,
        interval_end=now + timedelta(minutes=15),
        data_availability="available",
    )

    comp = compare_metric_observations(baseline, followup, criteria)
    assert comp.direction == "improved"
    assert comp.absolute_change == -2.0
    assert comp.relative_change_pct == -80.0
    assert comp.sample_sufficiency is True
    # Advisory note required
    assert any(
        "cannot be attributed to the read-only diagnostic" in n
        for n in comp.evaluation_notes
    )


def test_comparison_zero_baseline_undefined_relative_change():
    """Verify that zero baseline does not raise ZeroDivisionError and sets relative_change_pct to None."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria()
    baseline = MetricObservation(
        metric_name="HTTP Error Rate",
        expression="aegisops_sim_error_rate",
        unit="ratio",
        sample_count=3,
        mean_value=0.0,  # Zero baseline
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    followup = MetricObservation(
        metric_name="HTTP Error Rate",
        expression="aegisops_sim_error_rate",
        unit="ratio",
        sample_count=3,
        mean_value=0.05,
        interval_start=now,
        interval_end=now + timedelta(minutes=15),
        data_availability="available",
    )

    comp = compare_metric_observations(baseline, followup, criteria)
    assert comp.direction == "degraded"
    assert comp.absolute_change == 0.05
    assert comp.relative_change_pct is None
    assert any("mathematically undefined" in n for n in comp.evaluation_notes)


def test_comparison_service_up_availability():
    """Verify service availability transitions (1.0 vs <1.0)."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria()

    base_up = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=1,
        mean_value=1.0,
        interval_start=now,
        interval_end=now,
        data_availability="available",
    )
    post_up = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=1,
        mean_value=1.0,
        interval_start=now,
        interval_end=now,
        data_availability="available",
    )
    comp_stable = compare_metric_observations(base_up, post_up, criteria)
    assert comp_stable.direction == "unchanged"
    assert any("remained continuously UP" in n for n in comp_stable.evaluation_notes)

    post_down = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=1,
        mean_value=0.0,
        interval_start=now,
        interval_end=now,
        data_availability="available",
    )
    comp_degraded = compare_metric_observations(base_up, post_down, criteria)
    assert comp_degraded.direction == "degraded"


def test_comparison_service_up_availability_fractional_degradation_regression():
    """Verify that a drop in fractional availability (e.g. 0.88 to 0.8033) is classified as DEGRADED."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria()
    base_obs = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=25,
        mean_value=0.88,
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    post_obs = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=61,
        mean_value=0.8033,
        interval_start=now,
        interval_end=now + timedelta(minutes=15),
        data_availability="available",
    )
    comp = compare_metric_observations(base_obs, post_obs, criteria)
    assert comp.direction == "degraded"
    assert comp.absolute_change == -0.0767
    assert any(
        "exceeding stability tolerance" in note for note in comp.evaluation_notes
    )
    assert any("availability degradation" in note for note in comp.evaluation_notes)


def test_comparison_service_up_availability_fractional_improvement():
    """Verify that an increase in fractional availability (0.80 to 0.95) is classified as IMPROVED."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria()
    base_obs = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=20,
        mean_value=0.80,
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    post_obs = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=20,
        mean_value=0.95,
        interval_start=now,
        interval_end=now + timedelta(minutes=15),
        data_availability="available",
    )
    comp = compare_metric_observations(base_obs, post_obs, criteria)
    assert comp.direction == "improved"
    assert comp.absolute_change == 0.15
    assert any("availability improvement" in note for note in comp.evaluation_notes)
    assert any(
        "cannot be attributed to the read-only diagnostic operation" in note
        for note in comp.evaluation_notes
    )


def test_comparison_service_up_tolerance_boundary_unchanged():
    """Verify that small availability changes within tolerance remain UNCHANGED."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria()
    base_obs = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=20,
        mean_value=0.88,
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    post_obs = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=20,
        mean_value=0.885,  # +0.005, within 0.01 tolerance
        interval_start=now,
        interval_end=now + timedelta(minutes=15),
        data_availability="available",
    )
    comp = compare_metric_observations(base_obs, post_obs, criteria)
    assert comp.direction == "unchanged"
    assert any("stable within tolerance" in note for note in comp.evaluation_notes)

    # Continuously DOWN (0.0 to 0.0)
    base_down = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=20,
        mean_value=0.0,
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    post_down = MetricObservation(
        metric_name="Service Availability",
        expression="aegisops_sim_service_up",
        unit="binary",
        sample_count=20,
        mean_value=0.0,
        interval_start=now,
        interval_end=now + timedelta(minutes=15),
        data_availability="available",
    )
    comp_down = compare_metric_observations(base_down, post_down, criteria)
    assert comp_down.direction == "unchanged"
    assert any("continuously DOWN" in note for note in comp_down.evaluation_notes)


def test_comparison_missing_evidence_classified_insufficient_evidence():
    """Verify that missing observations or insufficient samples return 'insufficient_evidence'."""
    now = datetime.now(UTC)
    criteria = VerificationCriteria(min_samples_required=5)
    base_obs = MetricObservation(
        metric_name="API Response Latency",
        expression="aegisops_sim_latency_seconds",
        unit="s",
        sample_count=2,  # less than 5
        mean_value=1.5,
        interval_start=now - timedelta(minutes=15),
        interval_end=now,
        data_availability="available",
    )
    comp = compare_metric_observations(base_obs, None, criteria)
    assert comp.direction == "insufficient_evidence"
    assert comp.sample_sufficiency is False

    comp_sparse = compare_metric_observations(base_obs, base_obs, criteria)
    assert comp_sparse.direction == "insufficient_evidence"
    assert comp_sparse.sample_sufficiency is False


def test_evidence_sparse_baseline_coverage_detected():
    """Verify that sparse samples spanning a trivial fraction of the window are flagged."""
    from aegisops.integrations.prometheus import MetricSample
    from aegisops.verification.evidence import assess_telemetry_coverage

    now = datetime.now(UTC)
    start = now - timedelta(minutes=15)
    end = now
    # 2 samples 30s apart in a 15-minute window (900s) -> 30s / 900s = 3.3% coverage
    samples = [
        MetricSample(timestamp=start, value=1.0),
        MetricSample(timestamp=start + timedelta(seconds=30), value=1.0),
    ]
    criteria = VerificationCriteria(min_coverage_pct=20.0, min_samples_required=2)
    cov_pct, _max_gap, _first_ts, _last_ts, avail, notes = assess_telemetry_coverage(
        samples=samples,
        interval_start=start,
        interval_end=end,
        step="15s",
        criteria=criteria,
    )
    assert avail == "insufficient_coverage"
    assert cov_pct < 20.0
    assert any("below required threshold" in n for n in notes)


def test_evidence_large_timestamp_gap_detected():
    """Verify that gaps exceeding max_allowed_gap_seconds are flagged as insufficient_coverage."""
    from aegisops.integrations.prometheus import MetricSample
    from aegisops.verification.evidence import assess_telemetry_coverage

    now = datetime.now(UTC)
    start = now - timedelta(minutes=15)
    end = now
    # 2 samples 10 minutes (600s) apart -> exceeds 300s max allowed gap
    samples = [
        MetricSample(timestamp=start, value=1.0),
        MetricSample(timestamp=start + timedelta(minutes=10), value=1.0),
    ]
    criteria = VerificationCriteria(
        min_coverage_pct=20.0, max_allowed_gap_seconds=300, min_samples_required=2
    )
    _cov_pct, max_gap, _first_ts, _last_ts, avail, notes = assess_telemetry_coverage(
        samples=samples,
        interval_start=start,
        interval_end=end,
        step="15s",
        criteria=criteria,
    )
    assert avail == "insufficient_coverage"
    assert max_gap == 600.0
    assert any("exceeds allowable limit" in n for n in notes)


def test_evidence_unordered_timestamps_normalized():
    """Verify that out-of-order samples are sorted and evaluated without crashing."""
    from aegisops.integrations.prometheus import MetricSample
    from aegisops.verification.evidence import assess_telemetry_coverage

    now = datetime.now(UTC)
    start = now - timedelta(minutes=10)
    end = now
    # Samples in reverse order
    samples = [
        MetricSample(timestamp=end, value=1.0),
        MetricSample(timestamp=start + timedelta(minutes=5), value=1.1),
        MetricSample(timestamp=start, value=1.2),
    ]
    criteria = VerificationCriteria(
        min_coverage_pct=20.0, max_allowed_gap_seconds=400, min_samples_required=2
    )
    _cov_pct, _max_gap, first_ts, last_ts, avail, notes = assess_telemetry_coverage(
        samples=samples,
        interval_start=start,
        interval_end=end,
        step="15s",
        criteria=criteria,
    )
    assert avail == "available"
    assert first_ts == start
    assert last_ts == end
    assert any("sorted chronologically" in n for n in notes)


def test_step_parsing_and_cadence():
    """Verify parsing of Prometheus step intervals."""
    from aegisops.verification.evidence import parse_step_seconds

    assert parse_step_seconds("15s") == 15.0
    assert parse_step_seconds("1m") == 60.0
    assert parse_step_seconds("5m") == 300.0
    assert parse_step_seconds("1h") == 3600.0


def test_evidence_short_unfinished_followup_window():
    """Verify that an unfinished follow-up observation window returns insufficient_coverage."""
    now = datetime.now(UTC)
    execution = RemediationExecution(
        operation_id="inspect_latency_metrics",
        started_at=now - timedelta(minutes=2),
        completed_at=now
        - timedelta(minutes=1),  # Only 1 minute elapsed out of 15m (6.7%)
    )
    criteria = VerificationCriteria(followup_window_minutes=15, min_coverage_pct=20.0)

    obs, limits = retrieve_followup_evidence(execution, criteria)
    assert obs is not None
    assert obs.data_availability == "insufficient_coverage"
    assert obs.coverage_pct is not None and obs.coverage_pct < 20.0
    assert any("follow-up window has not fully elapsed" in lim for lim in limits)


def test_historical_record_backward_compatibility():
    """Verify that older stored verification records deserialize cleanly without error."""
    old_obs_data = {
        "metric_name": "API Response Latency",
        "expression": "aegisops_sim_latency_seconds",
        "unit": "s",
        "sample_count": 10,
        "mean_value": 1.25,
        "is_retrospective": False,
        "interval_start": "2026-10-16T12:00:00Z",
        "interval_end": "2026-10-16T12:15:00Z",
        "data_availability": "available",
        "label": "metric_observation",
    }
    obs = MetricObservation.model_validate(old_obs_data)
    assert obs.coverage_pct is None
    assert obs.max_gap_seconds is None
    assert obs.data_availability == "available"

    old_comp_data = {
        "metric_name": "API Response Latency",
        "unit": "s",
        "baseline_mean": 1.25,
        "followup_mean": 1.10,
        "absolute_change": -0.15,
        "relative_change_pct": -12.0,
        "direction": "undetermined",
        "sample_sufficiency": True,
        "evaluation_notes": ["legacy note"],
    }
    comp = MetricComparisonResult.model_validate(old_comp_data)
    assert comp.direction == "undetermined"
    assert comp.sample_sufficiency is True


# =========================================================================
# 4. Service & Persistence Integration Tests
# =========================================================================


@pytest.mark.asyncio
async def test_verify_live_diagnostic_execution_success(test_context):
    """Verify that a completed diagnostic execution is verified against Prometheus."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        operation_id="inspect_latency_metrics",
        mode=ExecutionMode.LIVE_DIAGNOSTIC,
        status=ExecutionStatus.DIAGNOSED,
    )

    criteria = VerificationCriteria(
        baseline_window_minutes=15, followup_window_minutes=15
    )
    now = datetime.now(UTC)

    with patch("aegisops.verification.evidence.query_prometheus_range") as mock_range:
        mock_range.return_value = [
            MetricSample(timestamp=now - timedelta(minutes=5), value=1.2),
            MetricSample(timestamp=now - timedelta(minutes=1), value=1.0),
        ]

        async with session_factory() as session:
            v_record, is_replay = await verifications.execute_verification(
                session=session,
                execution_id=execution.id,
                criteria=criteria,
                idempotency_key="verify-key-001",
                requested_by="sre-operator-dan",
            )

            assert is_replay is False
            assert v_record.execution_id == execution.id
            assert v_record.status == VerificationStatus.COMPLETED.value
            assert v_record.outcome == VerificationOutcome.DIAGNOSTIC_VERIFIED.value
            assert v_record.human_review_required is True
            assert v_record.remediation_success_confirmed is False
            assert v_record.baseline_evidence is not None
            assert v_record.followup_evidence is not None
            assert v_record.metric_comparison is not None

            # Verify audit events
            events = await verifications.get_verification_events(session, v_record.id)
            assert len(events) == 2
            assert events[0].event_type == VerificationEventType.STARTED.value
            assert events[1].event_type == VerificationEventType.COMPLETED.value
            assert events[1].outcome == VerificationOutcome.DIAGNOSTIC_VERIFIED.value


@pytest.mark.asyncio
async def test_verify_simulation_execution_returns_not_applicable(test_context):
    """Verify that simulation mode executions return 'not_applicable' outcome without calling Prometheus."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        operation_id="inspect_latency_metrics",
        mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SIMULATED,
    )

    criteria = VerificationCriteria()
    async with session_factory() as session:
        v_record, is_replay = await verifications.execute_verification(
            session=session,
            execution_id=execution.id,
            criteria=criteria,
            idempotency_key="verify-sim-001",
            requested_by="sre-operator-dan",
        )

        assert is_replay is False
        assert v_record.outcome == VerificationOutcome.NOT_APPLICABLE.value
        assert v_record.status == VerificationStatus.COMPLETED.value
        assert v_record.baseline_evidence is None
        assert any("simulation mode" in lim for lim in v_record.limitations)


@pytest.mark.asyncio
async def test_verify_running_execution_rejected(test_context):
    """Verify that attempting to verify an execution that is still RUNNING is rejected."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        status=ExecutionStatus.RUNNING,
    )

    criteria = VerificationCriteria()
    async with session_factory() as session:
        with pytest.raises(
            verifications.VerificationEligibilityError, match="not in a terminal state"
        ):
            await verifications.execute_verification(
                session=session,
                execution_id=execution.id,
                criteria=criteria,
                idempotency_key="verify-in-flight",
                requested_by="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_verify_tampered_plan_hash_rejected(test_context):
    """Verify that tampered plan hash between approval and execution is rejected."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    # Tamper with approval plan hash
    async with session_factory() as session:
        appr = await session.get(RemediationApproval, approval.id)
        assert appr is not None
        appr.plan_hash = "e" * 64
        await session.commit()

    criteria = VerificationCriteria()
    async with session_factory() as session:
        with pytest.raises(
            PlanIntegrityError, match="does not match approval plan hash"
        ):
            await verifications.execute_verification(
                session=session,
                execution_id=execution.id,
                criteria=criteria,
                idempotency_key="tamper-check",
                requested_by="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_verification_idempotent_replay(test_context):
    """Verify that identical re-execution returns the existing record with is_replay=True."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SIMULATED,
    )

    criteria = VerificationCriteria(baseline_window_minutes=15)
    async with session_factory() as session:
        first_record, is_replay_1 = await verifications.execute_verification(
            session=session,
            execution_id=execution.id,
            criteria=criteria,
            idempotency_key="replay-key-01",
            requested_by="sre-operator-dan",
        )
        assert is_replay_1 is False

        second_record, is_replay_2 = await verifications.execute_verification(
            session=session,
            execution_id=execution.id,
            criteria=criteria,
            idempotency_key="replay-key-01",
            requested_by="sre-operator-dan",
        )
        assert is_replay_2 is True
        assert first_record.id == second_record.id


@pytest.mark.asyncio
async def test_verification_idempotency_conflict_rejected(test_context):
    """Verify that reusing the same idempotency key with conflicting criteria raises IdempotencyConflictError."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SIMULATED,
    )

    crit_1 = VerificationCriteria(baseline_window_minutes=15)
    crit_2 = VerificationCriteria(baseline_window_minutes=60)

    async with session_factory() as session:
        await verifications.execute_verification(
            session=session,
            execution_id=execution.id,
            criteria=crit_1,
            idempotency_key="conflict-key-01",
            requested_by="sre-operator-dan",
        )

        with pytest.raises(
            IdempotencyConflictError, match="conflicting verification criteria"
        ):
            await verifications.execute_verification(
                session=session,
                execution_id=execution.id,
                criteria=crit_2,
                idempotency_key="conflict-key-01",
                requested_by="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_verification_concurrency_lock_protection(test_context):
    """Verify that concurrent verification requests for the same execution are blocked."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    # Insert a currently RUNNING verification
    async with session_factory() as session:
        active_v = ExecutionVerification(
            execution_id=execution.id,
            incident_id=incident.id,
            approval_id=approval.id,
            approved_plan_hash=execution.approved_plan_hash,
            operation_id=execution.operation_id,
            execution_mode=execution.mode,
            status=VerificationStatus.RUNNING.value,
            outcome=VerificationOutcome.INCONCLUSIVE.value,
            verification_criteria={},
            requested_by="sre-operator-dan",
            idempotency_key="in-flight-key",
            requested_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_ms=0,
            human_review_required=True,
            remediation_success_confirmed=False,
        )
        session.add(active_v)
        await session.commit()

        with pytest.raises(ConcurrencyConflictError, match="already in progress"):
            await verifications.execute_verification(
                session=session,
                execution_id=execution.id,
                criteria=VerificationCriteria(),
                idempotency_key="another-caller-key",
                requested_by="sre-operator-dan",
            )


@pytest.mark.asyncio
async def test_stale_verification_recovery_policy(test_context):
    """Verify that abandoned in-flight verifications are reconciled to TIMED_OUT."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    stale_time = datetime.now(UTC) - timedelta(minutes=10)
    async with session_factory() as session:
        stale_v = ExecutionVerification(
            execution_id=execution.id,
            incident_id=incident.id,
            approval_id=approval.id,
            approved_plan_hash=execution.approved_plan_hash,
            operation_id=execution.operation_id,
            execution_mode=execution.mode,
            status=VerificationStatus.RUNNING.value,
            outcome=VerificationOutcome.INCONCLUSIVE.value,
            verification_criteria={},
            requested_by="sre-operator-dan",
            idempotency_key="crashed-verifier-key",
            requested_at=stale_time,
            started_at=stale_time,
            completed_at=stale_time,
            duration_ms=0,
            human_review_required=True,
            remediation_success_confirmed=False,
        )
        session.add(stale_v)
        await session.commit()
        stale_id = stale_v.id

    async with session_factory() as session:
        reconciled = await verifications.reconcile_stale_verifications(
            session, threshold_minutes=5
        )
        assert reconciled == 1

        reloaded = await session.get(ExecutionVerification, stale_id)
        assert reloaded is not None
        assert reloaded.status == VerificationStatus.TIMED_OUT.value
        assert reloaded.outcome == VerificationOutcome.VERIFICATION_FAILED.value


# =========================================================================
# 5. API Endpoints & Role Authorization Tests
# =========================================================================


@pytest.mark.asyncio
async def test_api_verify_unauthenticated_rejected(test_context):
    """Verify unauthenticated requests return 401."""
    client, _ = test_context
    fake_id = uuid4()
    res = await client.post(
        f"/api/v1/executions/{fake_id}/verifications",
        json={"idempotency_key": "any-key-123"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_api_verify_insufficient_role_rejected(test_context):
    """Verify actors lacking verifier/operator/executor roles return 403."""
    client, _ = test_context
    fake_id = uuid4()
    res = await client.post(
        f"/api/v1/executions/{fake_id}/verifications",
        headers={"Authorization": "Bearer aegisops-dev-viewer-token"},
        json={"idempotency_key": "any-key-123"},
    )
    assert res.status_code == 403
    assert "lacks verification permission" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_verify_nonexistent_execution_returns_404(test_context):
    """Verify unknown execution ID returns 404."""
    client, _ = test_context
    fake_id = uuid4()
    res = await client.post(
        f"/api/v1/executions/{fake_id}/verifications",
        headers={"Authorization": "Bearer aegisops-dev-operator-token"},
        json={"idempotency_key": "valid-key-999"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_verify_simulation_success_lifecycle(test_context):
    """Verify complete API lifecycle for simulation execution verification."""
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SIMULATED,
    )

    res = await client.post(
        f"/api/v1/executions/{execution.id}/verifications",
        headers={"Authorization": "Bearer aegisops-dev-operator-token"},
        json={
            "idempotency_key": "api-verify-key-01",
            "criteria": {"baseline_window_minutes": 15},
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["outcome"] == "not_applicable"
    assert data["status"] == "completed"
    assert data["human_review_required"] is True
    assert data["remediation_success_confirmed"] is False
    v_id = data["id"]

    # Replay returns 200 OK
    res_replay = await client.post(
        f"/api/v1/executions/{execution.id}/verifications",
        headers={"Authorization": "Bearer aegisops-dev-operator-token"},
        json={
            "idempotency_key": "api-verify-key-01",
            "criteria": {"baseline_window_minutes": 15},
        },
    )
    assert res_replay.status_code == 200
    assert res_replay.json()["is_replay"] is True

    # Detail query
    res_get = await client.get(
        f"/api/v1/verifications/{v_id}",
        headers={"Authorization": "Bearer aegisops-dev-viewer-token"},
    )
    assert res_get.status_code == 200
    assert res_get.json()["id"] == v_id

    # List query
    res_list = await client.get(
        "/api/v1/verifications",
        headers={"Authorization": "Bearer aegisops-dev-viewer-token"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # Events query
    res_events = await client.get(
        f"/api/v1/verifications/{v_id}/events",
        headers={"Authorization": "Bearer aegisops-dev-viewer-token"},
    )
    assert res_events.status_code == 200
    assert len(res_events.json()) >= 1


# =========================================================================
# 6. Safety Regression Tests
# =========================================================================


@pytest.mark.asyncio
async def test_verification_never_mutates_incident_or_approval_status(test_context):
    """Verify that verification never alters PostgreSQL incident status or approval status."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(session_factory, incident.id, approval.id)

    now = datetime.now(UTC)
    with patch("aegisops.verification.evidence.query_prometheus_range") as mock_range:
        mock_range.return_value = [
            MetricSample(timestamp=now - timedelta(minutes=5), value=0.01),
            MetricSample(timestamp=now - timedelta(minutes=1), value=0.01),
        ]

        async with session_factory() as session:
            await verifications.execute_verification(
                session=session,
                execution_id=execution.id,
                criteria=VerificationCriteria(),
                idempotency_key="safety-immutability-check",
                requested_by="sre-operator-dan",
            )

            # Assert incident status remains strictly 'open'
            reloaded_inc = await session.get(Incident, incident.id)
            assert reloaded_inc is not None
            assert reloaded_inc.status == "open"

            # Assert approval status remains strictly 'approved'
            reloaded_appr = await session.get(RemediationApproval, approval.id)
            assert reloaded_appr is not None
            assert reloaded_appr.status == ApprovalStatus.APPROVED.value


@pytest.mark.asyncio
async def test_verification_retention_foreign_key_protection(test_context):
    """Verify that RESTRICT foreign keys prevent deleting executions when verification records exist."""
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)
    approval = await create_test_approval(session_factory, incident.id)
    execution = await create_test_execution(
        session_factory,
        incident.id,
        approval.id,
        mode=ExecutionMode.SIMULATION,
        status=ExecutionStatus.SIMULATED,
    )

    async with session_factory() as session:
        await verifications.execute_verification(
            session=session,
            execution_id=execution.id,
            criteria=VerificationCriteria(),
            idempotency_key="retention-check-key",
            requested_by="sre-operator-dan",
        )

        exec_obj = await session.get(RemediationExecution, execution.id)
        assert exec_obj is not None

        # Deleting execution must fail closed due to ON DELETE RESTRICT on execution_verifications.execution_id
        with pytest.raises(IntegrityError):
            await session.delete(exec_obj)
            await session.commit()
        await session.rollback()
