from uuid import uuid4

from aegisops.agents.rca import analyze_root_cause
from aegisops.integrations.gemini import GeminiError
from aegisops.workflows.rca import RCAHypothesis, RootCauseAnalysis


def sample_rca_state():
    return {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
        "alert_started_at": "2026-10-15T07:00:00+00:00",
        "investigation": {
            "summary": "High CPU utilization observed.",
            "observations": ["Current CPU is 94%."],
            "possible_causes": ["Workload spike."],
            "recommended_checks": ["Inspect CPU by process."],
            "confidence": "medium",
            "requires_human_review": True,
        },
        "historical_window": {
            "start": "2026-10-15T06:55:00+00:00",
            "end": "2026-10-15T07:05:00+00:00",
            "step": "15s",
        },
        "historical_evidence": {
            "window_start": "2026-10-15T06:55:00+00:00",
            "window_end": "2026-10-15T07:05:00+00:00",
            "step": "15s",
            "metrics": {
                "cpu_percent": {
                    "count": 4,
                    "min": 40.0,
                    "max": 95.0,
                    "avg": 70.0,
                    "first": 40.0,
                    "last": 95.0,
                    "samples": [
                        {"timestamp": "2026-10-15T06:55:00+00:00", "value": 40.0},
                        {"timestamp": "2026-10-15T07:00:00+00:00", "value": 95.0},
                    ],
                },
                "latency_seconds": {
                    "count": 4,
                    "min": 0.1,
                    "max": 1.5,
                    "avg": 0.8,
                    "first": 0.1,
                    "last": 1.5,
                    "samples": [],
                },
            },
        },
        "historical_evidence_error": None,
    }


def test_rca_returns_structured_result(monkeypatch):
    expected_rca = RootCauseAnalysis(
        summary="Historical CPU spike correlated with latency increase.",
        key_observations=["CPU increased from 40% to 95% at 07:00 UTC."],
        metric_changes=["Latency grew from 0.1s to 1.5s alongside CPU spike."],
        data_limitations=["No process-level profiling data available."],
        hypotheses=[
            RCAHypothesis(
                title="Synthetic Workload Spike",
                explanation="Workload increase drove simultaneous CPU and latency increases.",
                supporting_evidence=["Simultaneous rise in CPU and latency."],
                contradicting_evidence=[],
                missing_evidence=["Application process profiling", "HTTP access logs"],
                confidence="medium",
            ),
            RCAHypothesis(
                title="Resource Starvation",
                explanation="Memory or thread contention caused CPU churn.",
                supporting_evidence=["Latency spike."],
                contradicting_evidence=["Error rate remained baseline."],
                missing_evidence=["Thread dump telemetry"],
                confidence="low",
            ),
        ],
        most_likely_hypothesis="Synthetic Workload Spike",
        overall_confidence="medium",
        root_cause_confirmed=False,
        recommended_checks=[
            "Verify process thread pool usage.",
            "Check simulator scenario logs.",
        ],
        requires_human_review=True,
    )

    captured_prompt = {}

    def mock_generate_rca(prompt):
        captured_prompt["prompt"] = prompt
        return expected_rca

    monkeypatch.setattr("aegisops.agents.rca.generate_rca", mock_generate_rca)

    result = analyze_root_cause(sample_rca_state())

    assert result["rca"] is not None
    assert result["rca_error"] is None
    assert result["rca"]["root_cause_confirmed"] is False
    assert result["rca"]["requires_human_review"] is True
    assert len(result["rca"]["hypotheses"]) == 2

    prompt = captured_prompt["prompt"]
    assert "2026-10-15T06:55:00+00:00" in prompt
    assert "cpu_percent" in prompt
    assert "temporal correlation from causation" in prompt
    assert "simulator metrics are synthetic" in prompt


def test_rca_skips_when_historical_evidence_unavailable():
    state = sample_rca_state()
    state["historical_evidence"] = None
    state["historical_evidence_error"] = "Prometheus unavailable"

    result = analyze_root_cause(state)

    assert result["rca"] is None
    assert result["rca_error"] is not None


def test_rca_gemini_error_handling(monkeypatch):
    def mock_failing_gemini(prompt):
        raise GeminiError("Gemini API quota exceeded")

    monkeypatch.setattr("aegisops.agents.rca.generate_rca", mock_failing_gemini)

    result = analyze_root_cause(sample_rca_state())

    assert result["rca"] is None
    assert "Gemini API quota exceeded" in result["rca_error"]
