import json
import logging
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from aegisops.core.correlation import (
    _INCIDENT_ID_VAR,
    _REQUEST_ID_VAR,
)
from aegisops.core.logging import JSONFormatter
from aegisops.main import app
from aegisops.observability.metrics import (
    APPROVAL_DECISIONS,
    EXECUTION_REQUESTS,
    HTTP_DURATION,
    HTTP_REQUESTS,
    INCIDENTS_CREATED,
    SECURITY_DENIALS,
    WORKFLOW_NODE_DURATION,
    WORKFLOW_RUNS,
)


def test_json_formatter_structure_and_redaction():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="aegisops.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Processing secret token Bearer aegisops-dev-operator-token and aegisops_session=sec-abc12345",
        args=(),
        exc_info=None,
    )

    # Set correlation context
    test_req_id = str(uuid.uuid4())
    test_inc_id = str(uuid.uuid4())
    token_req = _REQUEST_ID_VAR.set(test_req_id)
    token_inc = _INCIDENT_ID_VAR.set(test_inc_id)

    try:
        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert "timestamp" in data
        assert "+00:00" in data["timestamp"] or data["timestamp"].endswith("Z")
        assert data["level"] == "INFO"
        assert data["service"] == "aegisops"
        assert data["request_id"] == test_req_id
        assert data["incident_id"] == test_inc_id

        # Check redactions
        assert "aegisops-dev-operator-token" not in data["message"]
        assert "REDACTED" in data["message"]
    finally:
        _REQUEST_ID_VAR.reset(token_req)
        _INCIDENT_ID_VAR.reset(token_inc)


@pytest.mark.asyncio
async def test_request_correlation_and_security_headers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Request with client-supplied valid UUID X-Request-ID
        client_req_id = str(uuid.uuid4())
        response = await client.get(
            "/api/v1/health", headers={"X-Request-ID": client_req_id}
        )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == client_req_id
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "no-store" in response.headers["Cache-Control"]

        # Request without X-Request-ID gets generated request ID
        response2 = await client.get("/api/v1/health")
        assert response2.status_code == 200
        generated_id = response2.headers.get("X-Request-ID")
        assert generated_id is not None
        assert generated_id.startswith("req_")


@pytest.mark.asyncio
async def test_health_and_readiness_probes(test_context):
    client, _ = test_context

    # Liveness check
    live_resp = await client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "healthy"

    # Readiness check
    ready_resp = await client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert "status" in ready_data
    assert "dependencies" in ready_data
    assert "database" in ready_data["dependencies"]
    assert "prometheus" in ready_data["dependencies"]
    assert "gemini_config" in ready_data["dependencies"]


def test_prometheus_metrics_bounded_cardinality():
    # Verify key Prometheus metrics exist and only have low-cardinality labels
    high_cardinality_forbidden_labels = {
        "incident_id",
        "incident_uuid",
        "execution_id",
        "approval_id",
        "token",
        "prompt",
        "raw_prompt",
        "url",
        "error_message",
    }

    metrics_to_check = [
        HTTP_REQUESTS,
        HTTP_DURATION,
        INCIDENTS_CREATED,
        WORKFLOW_RUNS,
        WORKFLOW_NODE_DURATION,
        APPROVAL_DECISIONS,
        EXECUTION_REQUESTS,
        SECURITY_DENIALS,
    ]

    for metric in metrics_to_check:
        for label in metric._labelnames:
            assert label not in high_cardinality_forbidden_labels, (
                f"Metric {metric._name} contains high cardinality label: {label}"
            )
