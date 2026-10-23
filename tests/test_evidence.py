from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aegisops.agents.evidence import collect_incident_evidence
from aegisops.integrations.prometheus import PrometheusError, query_prometheus
from aegisops.workflows.incident import incident_workflow


def sample_state():
    return {
        "incident_id": uuid4(),
        "title": "High CPU utilization detected",
        "severity": "high",
        "status": "open",
        "alert_name": "HighCPUUsage",
    }


def test_workflow_collects_evidence(monkeypatch):
    metrics = {
        "cpu_percent": 94.0,
        "latency_seconds": 0.25,
        "error_rate": 0.01,
        "service_up": 1.0,
    }

    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        lambda at=None: metrics,
    )

    from aegisops.workflows.investigation import InvestigationResult

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        lambda prompt: InvestigationResult(
            summary="CPU utilization is elevated.",
            observations=["Current CPU is 94%."],
            possible_causes=["Increased application workload."],
            recommended_checks=["Inspect process-level CPU usage."],
            confidence="medium",
            requires_human_review=True,
        ),
    )

    result = incident_workflow.invoke(sample_state())

    assert result["priority"] == "P2"
    assert result["evidence"] == metrics
    assert result["monitoring_error"] is None


def test_monitoring_failure_is_recorded(monkeypatch):
    def failed_collection(at=None):
        raise PrometheusError("Prometheus unavailable")

    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        failed_collection,
    )

    result = incident_workflow.invoke(sample_state())

    assert result["evidence"] == {}
    assert result["monitoring_error"] == "Prometheus unavailable"


def test_incident_without_alert_skips_monitoring():
    state = sample_state()
    del state["alert_name"]

    result = incident_workflow.invoke(state)

    assert result["priority"] == "P2"
    assert result["evidence"] == {}
    assert result["evidence_type"] == "unavailable"
    assert result["monitoring_error"] is None


def test_evidence_contains_collection_timestamp(monkeypatch):
    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        lambda at=None: {"cpu_percent": 94.0},
    )

    result = collect_incident_evidence(sample_state())

    assert result["evidence"]["cpu_percent"] == 94.0
    assert result["evidence_collected_at"] is not None
    assert result["monitoring_error"] is None


def test_historical_evidence_uses_alert_timestamp(monkeypatch):
    captured = {}

    def mock_metrics(at=None):
        captured["timestamp"] = at
        return {"cpu_percent": 94.0}

    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        mock_metrics,
    )

    state = sample_state()
    state["alert_started_at"] = "2026-10-15T07:00:00+00:00"

    result = collect_incident_evidence(state)

    assert captured["timestamp"] == datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    assert result["evidence_type"] == "historical"
    assert result["evidence"]["cpu_percent"] == 94.0


def test_missing_timestamp_uses_live_evidence(monkeypatch):
    captured = {}

    def mock_metrics(at=None):
        captured["timestamp"] = at
        return {"cpu_percent": 25.0}

    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        mock_metrics,
    )

    result = collect_incident_evidence(sample_state())

    assert captured["timestamp"] is None
    assert result["evidence_type"] == "live_snapshot"


def test_timezone_naive_timestamp_records_error():
    state = sample_state()
    state["alert_started_at"] = "2026-10-15T07:00:00"

    result = collect_incident_evidence(state)

    assert result["evidence"] == {}
    assert result["evidence_type"] == "unavailable"
    assert result["monitoring_error"] is not None
    assert "must include a timezone" in result["monitoring_error"]


def test_historical_monitoring_failure_is_recorded(monkeypatch):
    def failed_collection(at=None):
        raise PrometheusError("Historical data unavailable")

    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        failed_collection,
    )

    state = sample_state()
    state["alert_started_at"] = "2026-10-15T07:00:00+00:00"

    result = collect_incident_evidence(state)

    assert result["evidence"] == {}
    assert result["evidence_type"] == "unavailable"
    assert result["monitoring_error"] == "Historical data unavailable"


def test_query_prometheus_rejects_naive_timestamp():
    naive_dt = datetime(2026, 10, 15, 7, 0)
    with pytest.raises(ValueError, match="must be timezone-aware"):
        query_prometheus("aegisops_sim_cpu_usage_percent", at=naive_dt)
