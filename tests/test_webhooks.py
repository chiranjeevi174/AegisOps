from copy import deepcopy
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from aegisops.domain.incident import Incident

pytestmark = pytest.mark.asyncio

WEBHOOK_URL = "/api/v1/webhooks/alertmanager"

SAMPLE_ALERT = {
    "receiver": "aegisops-webhook",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "fingerprint": "test-cpu-alert-001",
            "labels": {
                "alertname": "HighCPUUsage",
                "severity": "high",
                "service": "simulator",
            },
            "annotations": {
                "summary": "High CPU utilization detected",
                "description": "CPU utilization exceeded 90%.",
            },
        }
    ],
}


async def test_valid_webhook_creates_incident(webhook_client):
    client, session_factory = webhook_client

    response = await client.post(WEBHOOK_URL, json=SAMPLE_ALERT)

    assert response.status_code == 200
    assert response.json()["processed"] == 1

    async with session_factory() as session:
        incident = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )

        assert incident is not None
        assert incident.source == "alertmanager"
        assert incident.severity == "high"
        assert incident.alert_state == "firing"


async def test_duplicate_alert_does_not_create_duplicate(webhook_client):
    client, session_factory = webhook_client

    first = await client.post(WEBHOOK_URL, json=SAMPLE_ALERT)
    second = await client.post(WEBHOOK_URL, json=SAMPLE_ALERT)

    assert first.status_code == 200
    assert second.status_code == 200

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )

        assert count == 1


async def test_resolved_alert_updates_existing_incident(webhook_client):
    client, session_factory = webhook_client

    await client.post(WEBHOOK_URL, json=SAMPLE_ALERT)

    resolved_payload = deepcopy(SAMPLE_ALERT)
    resolved_payload["status"] = "resolved"
    resolved_payload["alerts"][0]["status"] = "resolved"

    response = await client.post(WEBHOOK_URL, json=resolved_payload)

    assert response.status_code == 200
    assert response.json()["resolved"] == 1

    async with session_factory() as session:
        incident = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )

        assert incident.alert_state == "resolved"
        assert incident.status == "open"


async def test_missing_authentication_returns_401(test_context):
    client, _ = test_context

    response = await client.post(WEBHOOK_URL, json=SAMPLE_ALERT)

    assert response.status_code == 401


async def test_invalid_payload_returns_422(webhook_client):
    client, _ = webhook_client

    response = await client.post(
        WEBHOOK_URL,
        json={"receiver": "aegisops-webhook", "alerts": []},
    )

    assert response.status_code == 422


async def test_alert_starts_at_is_saved_and_preserved_on_duplicate(webhook_client):
    client, session_factory = webhook_client

    payload1 = deepcopy(SAMPLE_ALERT)
    payload1["alerts"][0]["startsAt"] = "2026-10-15T07:00:00Z"
    payload1["alerts"][0]["annotations"]["summary"] = "Original Title"
    payload1["alerts"][0]["labels"]["severity"] = "high"

    res1 = await client.post(WEBHOOK_URL, json=payload1)
    assert res1.status_code == 200

    async with session_factory() as session:
        incident1 = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )
        assert incident1 is not None
        assert incident1.alert_started_at == datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
        assert incident1.title == "Original Title"
        assert incident1.severity == "high"

    payload2 = deepcopy(SAMPLE_ALERT)
    payload2["alerts"][0]["startsAt"] = "2026-10-15T08:00:00Z"
    payload2["alerts"][0]["annotations"]["summary"] = "Changed Title"
    payload2["alerts"][0]["labels"]["severity"] = "low"

    res2 = await client.post(WEBHOOK_URL, json=payload2)
    assert res2.status_code == 200

    async with session_factory() as session:
        incident2 = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )
        assert incident2 is not None
        assert incident2.alert_started_at == datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
        assert incident2.title == "Original Title"
        assert incident2.severity == "high"
        assert incident2.status == "open"


async def test_subsequent_notification_populates_null_occurrence_timestamp(
    webhook_client,
):
    client, session_factory = webhook_client

    payload1 = deepcopy(SAMPLE_ALERT)
    res1 = await client.post(WEBHOOK_URL, json=payload1)
    assert res1.status_code == 200

    async with session_factory() as session:
        incident1 = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )
        assert incident1 is not None
        assert incident1.alert_started_at is None

    payload2 = deepcopy(SAMPLE_ALERT)
    payload2["alerts"][0]["startsAt"] = "2026-10-15T07:15:00Z"

    res2 = await client.post(WEBHOOK_URL, json=payload2)
    assert res2.status_code == 200

    async with session_factory() as session:
        incident2 = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )
        assert incident2 is not None
        assert incident2.alert_started_at == datetime(2026, 10, 15, 7, 15, tzinfo=UTC)


async def test_resolved_alert_preserves_timestamp_and_status_remains_open(
    webhook_client,
):
    client, session_factory = webhook_client

    await client.post(WEBHOOK_URL, json=SAMPLE_ALERT)

    resolved_payload = deepcopy(SAMPLE_ALERT)
    resolved_payload["status"] = "resolved"
    resolved_payload["alerts"][0]["status"] = "resolved"
    resolved_payload["alerts"][0]["startsAt"] = "2026-10-15T07:00:00Z"

    response = await client.post(WEBHOOK_URL, json=resolved_payload)
    assert response.status_code == 200

    async with session_factory() as session:
        incident = await session.scalar(
            select(Incident).where(Incident.alert_fingerprint == "test-cpu-alert-001")
        )
        assert incident is not None
        assert incident.alert_state == "resolved"
        assert incident.status == "open"
        assert incident.alert_started_at == datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
