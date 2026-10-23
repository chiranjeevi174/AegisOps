from uuid import uuid4

from aegisops.agents.investigation import investigate_incident
from aegisops.workflows.investigation import InvestigationResult


def sample_state():
    return {
        "incident_id": uuid4(),
        "title": "High CPU utilization",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
        "evidence": {
            "cpu_percent": 94.0,
            "latency_seconds": 0.25,
            "error_rate": 0.01,
            "service_up": 1.0,
        },
        "monitoring_error": None,
    }


def test_investigation_returns_structured_result(monkeypatch):
    expected = InvestigationResult(
        summary="High CPU utilization observed.",
        observations=["Current CPU utilization is 94%."],
        possible_causes=["Increased application workload."],
        recommended_checks=["Inspect CPU usage by process."],
        confidence="medium",
        requires_human_review=True,
    )

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        lambda prompt: expected,
    )

    result = investigate_incident(sample_state())

    assert result["investigation"]["confidence"] == "medium"
    assert result["investigation"]["requires_human_review"] is True
    assert result["investigation_error"] is None


def test_investigation_skips_missing_evidence():
    state = sample_state()
    state["evidence"] = {}

    result = investigate_incident(state)

    assert result["investigation"] is None
    assert result["investigation_error"] is not None


def test_investigation_passes_historical_context(monkeypatch):
    captured_prompt = {}

    def mock_generate(prompt):
        captured_prompt["prompt"] = prompt
        return InvestigationResult(
            summary="Historical high CPU observed.",
            observations=["Historical CPU is 94%."],
            possible_causes=["Workload spike at incident time."],
            recommended_checks=["Inspect historical process logs."],
            confidence="high",
            requires_human_review=True,
        )

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        mock_generate,
    )

    state = sample_state()
    state["alert_started_at"] = "2026-10-15T07:00:00+00:00"
    state["evidence_type"] = "historical"

    result = investigate_incident(state)

    assert result["investigation"] is not None
    assert (
        "Historical evidence represents Prometheus samples" in captured_prompt["prompt"]
    )
    assert "2026-10-15T07:00:00+00:00" in captured_prompt["prompt"]
    assert "historical" in captured_prompt["prompt"]
