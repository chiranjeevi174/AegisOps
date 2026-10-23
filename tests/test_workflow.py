from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aegisops.integrations.gemini import GeminiError
from aegisops.integrations.prometheus import MetricSample
from aegisops.workflows.incident import incident_workflow
from aegisops.workflows.investigation import InvestigationResult
from aegisops.workflows.rca import RCAHypothesis, RootCauseAnalysis
from aegisops.workflows.remediation import RemediationAction, RemediationPlan


@pytest.mark.parametrize(
    ("severity", "priority", "escalation"),
    [
        ("critical", "P1", True),
        ("high", "P2", True),
        ("medium", "P3", False),
        ("low", "P4", False),
    ],
)
def test_incident_triage(severity, priority, escalation):
    state = {
        "incident_id": uuid4(),
        "title": "Service performance degradation",
        "severity": severity,
        "status": "open",
    }

    result = incident_workflow.invoke(state)

    assert result["priority"] == priority
    assert result["requires_escalation"] is escalation
    assert result["incident_id"] == state["incident_id"]


def test_workflow_runs_historical_rca_when_timestamp_available(monkeypatch):
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

    monkeypatch.setattr(
        "aegisops.agents.rca.generate_rca",
        lambda prompt: RootCauseAnalysis(
            summary="CPU spike confirmed in historical window.",
            key_observations=["CPU rose to 88%."],
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

    monkeypatch.setattr(
        "aegisops.agents.remediation.generate_remediation_plan",
        lambda prompt: RemediationPlan(
            incident_summary="CPU spike.",
            planning_basis="RCA.",
            recommended_actions=[
                RemediationAction(
                    title="Inspect CPU processes",
                    description="Check process CPU consumption",
                    rationale="Identify top CPU consumer",
                    supporting_evidence=[],
                    prerequisites=[],
                    risk_level="low",
                    action_type="diagnostic",
                    validation_steps=[],
                    rollback_considerations=[],
                    requires_human_approval=True,
                )
            ],
            missing_information=[],
            overall_risk="low",
            requires_human_approval=True,
            execution_enabled=False,
        ),
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

    assert result["priority"] == "P2"
    assert result["investigation"] is not None
    assert result["historical_evidence"] is not None
    assert result["rca"] is not None
    assert result["rca"]["most_likely_hypothesis"] == "Load Surge"
    assert result["rca"]["root_cause_confirmed"] is False
    assert result["remediation_plan"] is not None
    assert result["remediation_plan"]["execution_enabled"] is False
    assert result["remediation_plan"]["requires_human_approval"] is True


def test_workflow_skips_rca_when_timestamp_missing(monkeypatch):
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

    state = {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
        # No alert_started_at
    }

    result = incident_workflow.invoke(state)

    assert result["investigation"] is not None
    assert result.get("historical_evidence") is None
    assert result.get("rca") is None


def test_workflow_skips_rca_when_historical_data_unavailable(monkeypatch):
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

    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        lambda expression, start, end, step="15s": [],
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

    assert result["investigation"] is not None
    assert result.get("historical_evidence") is None
    assert result.get("rca") is None
    assert result.get("historical_evidence_error") is not None


def test_workflow_gemini_failure_does_not_crash_workflow(monkeypatch):
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

    # Workflow completed safely
    assert result["investigation"] is not None
    assert result["historical_evidence"] is not None
    assert result.get("rca") is None
    assert "Gemini quota exhausted" in result.get("rca_error", "")
