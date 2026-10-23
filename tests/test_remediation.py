from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegisops.agents.remediation import plan_remediation
from aegisops.integrations.gemini import GeminiError
from aegisops.integrations.prometheus import MetricSample
from aegisops.services.remediation_safety import (
    RemediationSafetyError,
    validate_remediation_safety,
    validate_remediation_safety_node,
)
from aegisops.workflows.incident import incident_workflow
from aegisops.workflows.investigation import InvestigationResult
from aegisops.workflows.rca import RCAHypothesis, RootCauseAnalysis
from aegisops.workflows.remediation import RemediationAction, RemediationPlan


def create_sample_action(
    title: str = "Inspect service resource allocation",
    action_type: str = "diagnostic",
    risk_level: str = "low",
    requires_human_approval: bool = True,
    description: str = "Check CPU and memory limits on the pod.",
    rationale: str = "RCA indicates possible CPU throttle.",
    validation_steps: list[str] | None = None,
    rollback_considerations: list[str] | None = None,
) -> RemediationAction:
    return RemediationAction(
        title=title,
        description=description,
        rationale=rationale,
        supporting_evidence=["Historical CPU spike to 95%"],
        prerequisites=["Access to observability dashboards"],
        risk_level=risk_level,  # pyright: ignore[reportArgumentType]
        action_type=action_type,  # pyright: ignore[reportArgumentType]
        validation_steps=validation_steps or ["Verify CPU metrics normalize"],
        rollback_considerations=rollback_considerations
        or ["No rollback required for read-only diagnostics"],
        requires_human_approval=requires_human_approval,
    )


def create_sample_plan(
    actions: list[RemediationAction] | None = None,
    overall_risk: str = "low",
    requires_human_approval: bool = True,
    execution_enabled: bool = False,
    incident_summary: str = "Elevated latency correlated with synthetic CPU load.",
    planning_basis: str = "Historical Prometheus telemetry and RCA hypothesis.",
) -> RemediationPlan:
    return RemediationPlan(
        incident_summary=incident_summary,
        planning_basis=planning_basis,
        recommended_actions=[create_sample_action()] if actions is None else actions,
        missing_information=["Application thread dump", "Database slow query log"],
        overall_risk=overall_risk,  # pyright: ignore[reportArgumentType]
        requires_human_approval=requires_human_approval,
        execution_enabled=execution_enabled,
    )


def sample_workflow_state():
    return {
        "incident_id": uuid4(),
        "title": "High API latency detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighLatencyAlert",
        "alert_started_at": "2026-10-15T07:00:00+00:00",
        "investigation": {
            "summary": "API latency elevated to 1.8s.",
            "confidence": "medium",
            "observations": ["P99 latency above SLA threshold."],
            "possible_causes": ["Downstream delay", "CPU contention"],
            "recommended_checks": ["Check upstream load"],
            "requires_human_review": True,
        },
        "rca": {
            "summary": "Historical analysis correlates latency spike with CPU surge.",
            "most_likely_hypothesis": "CPU Contention",
            "overall_confidence": "medium",
            "root_cause_confirmed": False,
            "requires_human_review": True,
            "key_observations": ["CPU surged at 07:00 UTC"],
            "metric_changes": ["Latency rose from 0.1s to 1.8s"],
            "data_limitations": ["No APM tracing data"],
            "hypotheses": [
                {
                    "title": "CPU Contention",
                    "explanation": "High CPU utilization delayed request processing.",
                    "supporting_evidence": ["Simultaneous CPU and latency spikes"],
                    "contradicting_evidence": [],
                    "missing_evidence": ["Thread pool metrics"],
                    "confidence": "medium",
                }
            ],
            "recommended_checks": ["Inspect CPU usage per process"],
        },
        "rca_error": None,
    }


# =========================================================================
# 1. Structured Output and Model Invariant Tests
# =========================================================================


def test_remediation_action_valid():
    action = create_sample_action()
    assert action.title == "Inspect service resource allocation"
    assert action.risk_level == "low"
    assert action.action_type == "diagnostic"
    assert action.requires_human_approval is True


def test_remediation_action_rejects_human_approval_waiver():
    with pytest.raises(ValidationError, match="Human approval is mandatory"):
        create_sample_action(requires_human_approval=False)


def test_remediation_plan_valid():
    plan = create_sample_plan()
    assert plan.execution_enabled is False
    assert plan.requires_human_approval is True
    assert len(plan.recommended_actions) == 1


def test_remediation_plan_rejects_execution_enabled():
    with pytest.raises(ValidationError, match="Execution cannot be enabled"):
        create_sample_plan(execution_enabled=True)


def test_remediation_plan_rejects_human_approval_waiver():
    with pytest.raises(ValidationError, match="Human approval is mandatory"):
        create_sample_plan(requires_human_approval=False)


def test_remediation_plan_action_count_bounds():
    with pytest.raises(ValidationError):
        create_sample_plan(actions=[])

    actions = [create_sample_action(title=f"Action {i}") for i in range(6)]
    with pytest.raises(ValidationError):
        create_sample_plan(actions=actions)


def test_remediation_plan_invalid_risk_or_action_type():
    with pytest.raises(ValidationError):
        create_sample_action(risk_level="extreme")  # pyright: ignore[reportArgumentType]

    with pytest.raises(ValidationError):
        create_sample_action(action_type="automated_reboot")  # pyright: ignore[reportArgumentType]


# =========================================================================
# 2. Deterministic Safety Validator Tests
# =========================================================================


def test_safety_validator_accepts_valid_advisory_plan():
    plan = create_sample_plan()
    validated = validate_remediation_safety(plan, rca={"overall_confidence": "medium"})
    assert validated.execution_enabled is False
    assert validated.requires_human_approval is True


def test_safety_validator_rejects_operational_change_with_low_rca_confidence():
    op_action = create_sample_action(
        title="Scale deployment replicas",
        action_type="operational_change",
        risk_level="medium",
    )
    plan = create_sample_plan(actions=[op_action])

    with pytest.raises(
        RemediationSafetyError,
        match="proposes an operational change.*insufficient or low-confidence",
    ):
        validate_remediation_safety(plan, rca={"overall_confidence": "low"})

    with pytest.raises(
        RemediationSafetyError,
        match="proposes an operational change.*insufficient or low-confidence",
    ):
        validate_remediation_safety(plan, rca=None)


def test_safety_validator_allows_operational_change_with_medium_or_high_confidence():
    op_action = create_sample_action(
        title="Adjust pod CPU limits",
        action_type="operational_change",
        risk_level="medium",
    )
    plan = create_sample_plan(actions=[op_action])

    validated = validate_remediation_safety(plan, rca={"overall_confidence": "medium"})
    assert validated is not None


@pytest.mark.parametrize(
    "forbidden_pattern",
    [
        "rm -rf /tmp/data",
        "kubectl delete pod my-pod",
        "kubectl apply -f deployment.yaml",
        "sudo systemctl restart nginx",
        "drop table users",
        "kill -9 1234",
        "chmod 777 /etc/config",
    ],
)
def test_safety_validator_rejects_banned_command_patterns(forbidden_pattern):
    unsafe_action = create_sample_action(
        title="Apply quick mitigation",
        description=f"Run command: {forbidden_pattern}",
    )
    plan = create_sample_plan(actions=[unsafe_action])

    with pytest.raises(
        RemediationSafetyError, match="forbidden executable or destructive pattern"
    ):
        validate_remediation_safety(plan, rca={"overall_confidence": "medium"})


@pytest.mark.parametrize(
    "resolution_claim",
    [
        "remediation completed successfully",
        "incident is resolved after this check",
        "incident is closed",
        "status changed to resolved",
    ],
)
def test_safety_validator_rejects_resolution_claims(resolution_claim):
    unsafe_action = create_sample_action(
        title="Check status",
        description=f"Note: {resolution_claim}",
    )
    plan = create_sample_plan(actions=[unsafe_action])

    with pytest.raises(
        RemediationSafetyError, match="improperly claims incident resolution"
    ):
        validate_remediation_safety(plan, rca={"overall_confidence": "medium"})


def test_safety_validator_node_blocks_unsafe_plan():
    unsafe_plan_dict = {
        "incident_summary": "Incident resolved automatically",
        "planning_basis": "RCA",
        "recommended_actions": [
            {
                "title": "Purge caches",
                "description": "rm -rf /var/cache/*",
                "rationale": "Clear stale memory",
                "supporting_evidence": [],
                "prerequisites": [],
                "risk_level": "high",
                "action_type": "diagnostic",
                "validation_steps": [],
                "rollback_considerations": [],
                "requires_human_approval": True,
            }
        ],
        "missing_information": [],
        "overall_risk": "high",
        "requires_human_approval": True,
        "execution_enabled": False,
    }

    state = {
        "remediation_plan": unsafe_plan_dict,
        "remediation_error": None,
        "rca": {"overall_confidence": "medium"},
    }

    result = validate_remediation_safety_node(state)
    assert result["remediation_plan"] is None
    assert "Safety validation failed" in result["remediation_error"]


# =========================================================================
# 3. Remediation Planning Agent Tests
# =========================================================================


def test_plan_remediation_skips_when_rca_missing():
    state = sample_workflow_state()
    state["rca"] = None
    state["rca_error"] = "Historical metrics missing"

    result = plan_remediation(state)
    assert result["remediation_plan"] is None
    assert "Historical metrics missing" in result["remediation_error"]


def test_plan_remediation_invokes_gemini_with_rca_context(monkeypatch):
    captured = {}
    sample_plan = create_sample_plan()

    def mock_generate(prompt):
        captured["prompt"] = prompt
        return sample_plan

    monkeypatch.setattr(
        "aegisops.agents.remediation.generate_remediation_plan", mock_generate
    )

    state = sample_workflow_state()
    result = plan_remediation(state)

    assert result["remediation_plan"] is not None
    assert result["remediation_error"] is None
    assert "CPU Contention" in captured["prompt"]
    assert "simultaneous cpu and latency spikes" in captured["prompt"].lower()
    assert "requires_human_approval to true" in captured["prompt"]
    assert "execution_enabled to false" in captured["prompt"]


def test_plan_remediation_handles_gemini_failure(monkeypatch):
    def mock_failing_gemini(prompt):
        raise GeminiError("Gemini API rate limit exceeded")

    monkeypatch.setattr(
        "aegisops.agents.remediation.generate_remediation_plan", mock_failing_gemini
    )

    state = sample_workflow_state()
    result = plan_remediation(state)

    assert result["remediation_plan"] is None
    assert "Gemini API rate limit exceeded" in result["remediation_error"]


# =========================================================================
# 4. End-to-End Workflow Integration Tests
# =========================================================================


def test_workflow_runs_full_pipeline_to_remediation_planning(monkeypatch):
    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        lambda at=None: {"cpu_percent": 92.0},
    )

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        lambda prompt: InvestigationResult(
            summary="High CPU observed.",
            observations=["Live CPU is 92%."],
            possible_causes=["Workload surge."],
            recommended_checks=["Inspect CPU."],
            confidence="medium",
            requires_human_review=True,
        ),
    )

    sample_ts = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        lambda expression, start, end, step="15s": [
            MetricSample(timestamp=sample_ts, value=91.0)
        ],
    )

    monkeypatch.setattr(
        "aegisops.agents.rca.generate_rca",
        lambda prompt: RootCauseAnalysis(
            summary="CPU spike confirmed in historical window.",
            key_observations=["CPU rose to 91%."],
            metric_changes=["CPU elevated."],
            data_limitations=[],
            hypotheses=[
                RCAHypothesis(
                    title="Load Surge",
                    explanation="Elevated traffic driven CPU.",
                    supporting_evidence=["Elevated CPU"],
                    contradicting_evidence=[],
                    missing_evidence=[],
                    confidence="medium",
                )
            ],
            most_likely_hypothesis="Load Surge",
            overall_confidence="medium",
            root_cause_confirmed=False,
            recommended_checks=["Check simulator."],
            requires_human_review=True,
        ),
    )

    sample_plan = create_sample_plan(
        actions=[
            create_sample_action(
                title="Review traffic concurrency and CPU saturation",
                action_type="diagnostic",
                risk_level="low",
            )
        ]
    )

    monkeypatch.setattr(
        "aegisops.agents.remediation.generate_remediation_plan",
        lambda prompt: sample_plan,
    )

    state = {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
        "alert_started_at": "2026-10-15T07:00:00+00:00",
    }

    result = incident_workflow.invoke(state)

    # Validate full workflow execution
    assert result["investigation"] is not None
    assert result["historical_evidence"] is not None
    assert result["rca"] is not None
    assert result["remediation_plan"] is not None
    assert result["remediation_error"] is None

    # Validate safety properties on final plan
    plan = result["remediation_plan"]
    assert plan["execution_enabled"] is False
    assert plan["requires_human_approval"] is True
    assert len(plan["recommended_actions"]) == 1
    action = plan["recommended_actions"][0]
    assert action["requires_human_approval"] is True
    assert action["action_type"] == "diagnostic"


def test_workflow_skips_remediation_when_rca_fails(monkeypatch):
    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        lambda at=None: {"cpu_percent": 90.0},
    )

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        lambda prompt: InvestigationResult(
            summary="High CPU observed.",
            observations=["Live CPU is 90%."],
            possible_causes=["Workload spike."],
            recommended_checks=["Inspect CPU."],
            confidence="medium",
            requires_human_review=True,
        ),
    )

    sample_ts = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        lambda expression, start, end, step="15s": [
            MetricSample(timestamp=sample_ts, value=88.0)
        ],
    )

    def mock_failing_rca(prompt):
        raise GeminiError("Gemini quota exhausted")

    monkeypatch.setattr("aegisops.agents.rca.generate_rca", mock_failing_rca)

    state = {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
        "alert_started_at": "2026-10-15T07:00:00+00:00",
    }

    result = incident_workflow.invoke(state)

    # Workflow completed safely without crashing
    assert result["investigation"] is not None
    assert result["rca"] is None
    assert "Gemini quota exhausted" in result.get("rca_error", "")
    assert result.get("remediation_plan") is None


def test_workflow_blocks_unsafe_remediation_plan_at_safety_node(monkeypatch):
    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        lambda at=None: {"cpu_percent": 90.0},
    )

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        lambda prompt: InvestigationResult(
            summary="CPU spike.",
            observations=[],
            possible_causes=[],
            recommended_checks=[],
            confidence="medium",
            requires_human_review=True,
        ),
    )

    sample_ts = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        lambda expression, start, end, step="15s": [
            MetricSample(timestamp=sample_ts, value=88.0)
        ],
    )

    monkeypatch.setattr(
        "aegisops.agents.rca.generate_rca",
        lambda prompt: RootCauseAnalysis(
            summary="CPU spike.",
            key_observations=[],
            metric_changes=[],
            data_limitations=[],
            hypotheses=[
                RCAHypothesis(
                    title="Spike",
                    explanation="Spike",
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    missing_evidence=[],
                    confidence="medium",
                )
            ],
            most_likely_hypothesis="Spike",
            overall_confidence="medium",
            root_cause_confirmed=False,
            recommended_checks=[],
            requires_human_review=True,
        ),
    )

    # Return a plan containing a forbidden shell command
    unsafe_plan = create_sample_plan(
        actions=[
            create_sample_action(
                title="Restart service",
                description="Execute: sudo systemctl restart aegisops",
            )
        ]
    )

    monkeypatch.setattr(
        "aegisops.agents.remediation.generate_remediation_plan",
        lambda prompt: unsafe_plan,
    )

    state = {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
        "alert_started_at": "2026-10-15T07:00:00+00:00",
    }

    result = incident_workflow.invoke(state)

    # Previous results are preserved
    assert result["investigation"] is not None
    assert result["rca"] is not None
    # Unsafe plan was rejected and blocked
    assert result["remediation_plan"] is None
    assert "Safety validation failed" in result["remediation_error"]
    assert "sudo" in result["remediation_error"]
