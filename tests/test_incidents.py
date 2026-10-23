from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aegisops.domain.incident import Incident
from aegisops.integrations.prometheus import MetricSample
from aegisops.services.incidents import IncidentNotFoundError, run_incident_workflow
from aegisops.workflows.investigation import InvestigationResult
from aegisops.workflows.rca import RCAHypothesis, RootCauseAnalysis
from aegisops.workflows.remediation import RemediationAction, RemediationPlan

pytestmark = pytest.mark.asyncio


async def test_manual_incident_creation(test_context):
    client, _ = test_context

    payload = {
        "title": "Database connection failure",
        "description": "Application cannot connect to PostgreSQL.",
        "severity": "critical",
    }

    response = await client.post(
        "/api/v1/incidents",
        json=payload,
    )

    assert response.status_code == 201

    incident = response.json()

    assert incident["source"] == "manual"
    assert incident["status"] == "open"

    response = await client.get("/api/v1/incidents")

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_run_incident_workflow_from_database(test_context, monkeypatch):
    _, session_factory = test_context

    incident_id = uuid4()
    started_at = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)

    async with session_factory() as session:
        incident = Incident(
            id=incident_id,
            title="High CPU utilization detected",
            description="CPU load spike detected by Alertmanager.",
            severity="high",
            status="open",
            source="alertmanager",
            alert_fingerprint="test-fp-123",
            alert_started_at=started_at,
        )
        session.add(incident)
        await session.commit()

    monkeypatch.setattr(
        "aegisops.agents.evidence.collect_metrics",
        lambda at=None: {"cpu_percent": 95.0},
    )

    monkeypatch.setattr(
        "aegisops.agents.investigation.generate_investigation",
        lambda prompt: InvestigationResult(
            summary="CPU elevated.",
            observations=["95% CPU."],
            possible_causes=["Workload."],
            recommended_checks=["Inspect."],
            confidence="medium",
            requires_human_review=True,
        ),
    )

    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        lambda expression, start, end, step="15s": [
            MetricSample(timestamp=started_at, value=95.0)
        ],
    )

    monkeypatch.setattr(
        "aegisops.agents.rca.generate_rca",
        lambda prompt: RootCauseAnalysis(
            summary="RCA summary.",
            key_observations=["Obs."],
            metric_changes=["Change."],
            data_limitations=[],
            hypotheses=[
                RCAHypothesis(
                    title="Hypothesis 1",
                    explanation="Expl.",
                    supporting_evidence=["CPU 95%"],
                    contradicting_evidence=[],
                    missing_evidence=[],
                    confidence="medium",
                )
            ],
            overall_confidence="medium",
            root_cause_confirmed=False,
            recommended_checks=["Checks."],
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

    async with session_factory() as session:
        result = await run_incident_workflow(session, incident_id)

    assert result["incident_id"] == incident_id
    assert result["priority"] == "P2"
    assert result["alert_name"] == "HighCPUUsage"
    assert result["alert_started_at"] == started_at.isoformat()
    assert result["rca"] is not None
    assert result["rca"]["root_cause_confirmed"] is False
    assert result["remediation_plan"] is not None
    assert result["remediation_plan"]["execution_enabled"] is False
    assert result["remediation_plan"]["requires_human_approval"] is True

    # Verify existing incident in DB was NOT modified
    async with session_factory() as session:
        db_incident = await session.get(Incident, incident_id)
        assert db_incident is not None
        assert db_incident.status == "open"
        assert db_incident.severity == "high"


async def test_run_incident_workflow_not_found(test_context):
    _, session_factory = test_context

    non_existent_id = uuid4()
    async with session_factory() as session:
        with pytest.raises(IncidentNotFoundError):
            await run_incident_workflow(session, non_existent_id)
