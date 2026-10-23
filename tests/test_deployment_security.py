"""Production-oriented deployment security smoke test suite for AegisOps."""

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from aegisops.core.config import get_settings
from aegisops.core.rate_limit import SlidingWindowRateLimiter
from aegisops.main import app


@pytest.mark.asyncio
async def test_production_persona_switching_disabled(test_context):
    """Verifies that development persona listing and session identity selection are rejected in production."""
    client, _ = test_context
    with patch("aegisops.core.config.Settings.dev_persona_switching_allowed", False):
        # 1. Listing personas returns 403
        resp = await client.get("/api/v1/auth/personas")
        assert resp.status_code == 403
        assert "persona switching" in resp.json()["detail"].lower()

        # 2. Creating session via identity returns 403
        resp2 = await client.post(
            "/api/v1/auth/session", json={"identity": "sre-operator-dan"}
        )
        assert resp2.status_code == 403
        assert "disabled" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_production_csrf_enforcement_and_secure_cookie(test_context):
    """Verifies that cookie sessions enforce session-bound CSRF and set Secure cookie flag in production."""
    _client, _ = test_context
    with (
        patch("aegisops.core.config.Settings.is_production", True),
        patch.object(get_settings(), "session_cookie_secure", True),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://testserver"
        ) as https_client:
            # 1. Establish session with valid token over HTTPS
            login_resp = await https_client.post(
                "/api/v1/auth/session", json={"token": "aegisops-dev-operator-token"}
            )
            assert login_resp.status_code == 200

            # Verify Secure cookie flag in production
            session_cookie_header = login_resp.headers.get("set-cookie", "")
            assert "aegisops_session=" in session_cookie_header
            assert "Secure" in session_cookie_header
            assert "HttpOnly" in session_cookie_header

            csrf_token = login_resp.json()["csrf_token"]
            assert csrf_token is not None

            # 2. State-changing request using cookie auth without CSRF token -> 403
            fail_resp = await https_client.post(
                "/api/v1/auth/logout",
                headers={"Origin": "https://testserver"},
            )
            assert fail_resp.status_code == 403
            assert "csrf" in fail_resp.json()["detail"].lower()

            # 3. State-changing request with invalid CSRF token -> 403
            invalid_resp = await https_client.post(
                "/api/v1/auth/logout",
                headers={
                    "Origin": "https://testserver",
                    "X-CSRF-Token": "bad-csrf-token",
                },
            )
            assert invalid_resp.status_code == 403
            assert "csrf token" in invalid_resp.json()["detail"].lower()

            # 4. State-changing request with valid session-bound CSRF token -> succeeds
            valid_resp = await https_client.post(
                "/api/v1/auth/logout",
                headers={"Origin": "https://testserver", "X-CSRF-Token": csrf_token},
            )
            assert valid_resp.status_code == 200


@pytest.mark.asyncio
async def test_production_viewer_cannot_analyze_incident(test_context):
    """Verifies that a viewer role is forbidden from triggering LLM incident analysis."""
    client, _ = test_context
    resp = await client.post(
        "/api/v1/incidents/00000000-0000-0000-0000-000000000001/analyze",
        headers={"Authorization": "Bearer aegisops-dev-viewer-token"},
    )
    assert resp.status_code == 403
    assert "lacks incident analysis permission" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_production_security_headers_and_cache_control(test_context):
    """Verifies presence of defensive security headers and cache control on API endpoints."""
    client, _ = test_context
    with patch("aegisops.core.config.Settings.is_production", True):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "no-store" in resp.headers.get("cache-control", "")
        assert resp.headers.get("x-request-id") is not None


@pytest.mark.asyncio
async def test_production_live_diagnostics_disabled(test_context):
    """Verifies that live diagnostics cannot be invoked when live_diagnostics_enabled is False."""
    client, _ = test_context
    settings = get_settings()
    orig = settings.live_diagnostics_enabled
    object.__setattr__(settings, "live_diagnostics_enabled", False)
    try:
        resp = await client.post(
            "/api/v1/executions/diagnose",
            json={
                "approval_id": "00000000-0000-0000-0000-000000000001",
                "incident_id": "00000000-0000-0000-0000-000000000002",
                "operation_id": "inspect_cpu_metrics",
                "recommendation_index": 1,
                "idempotency_key": "prod-smoke-diag-key",
            },
            headers={"Authorization": "Bearer aegisops-dev-operator-token"},
        )
        assert resp.status_code == 403
        assert "Live diagnostics are disabled" in resp.json()["detail"]
    finally:
        object.__setattr__(settings, "live_diagnostics_enabled", orig)


def test_production_rate_limiting_sliding_window():
    """Verifies that rate limiting returns False when the sliding-window threshold is exceeded."""
    limiter = SlidingWindowRateLimiter()
    client_key = "prod-smoke-test-client"

    allowed1, remaining1, _ = limiter.check_rate_limit(
        client_key, max_requests=3, window_seconds=60
    )
    assert allowed1 is True
    assert remaining1 == 2

    allowed2, remaining2, _ = limiter.check_rate_limit(
        client_key, max_requests=3, window_seconds=60
    )
    assert allowed2 is True
    assert remaining2 == 1

    allowed3, remaining3, _ = limiter.check_rate_limit(
        client_key, max_requests=3, window_seconds=60
    )
    assert allowed3 is True
    assert remaining3 == 0

    # 4th request within window must be rejected
    allowed4, remaining4, retry_after = limiter.check_rate_limit(
        client_key, max_requests=3, window_seconds=60
    )
    assert allowed4 is False
    assert remaining4 == 0
    assert retry_after > 0


def test_no_credentials_in_frontend_production_bundle():
    """Verifies that compiled frontend assets in dist/ do not leak backend secrets."""
    dist_dir = Path("frontend/dist/assets")
    if not dist_dir.exists():
        pytest.skip("frontend/dist/assets does not exist; run npm run build first")

    sensitive_patterns = [
        "aegisops_local",
        "POSTGRES_PASSWORD",
        "ALERTMANAGER_WEBHOOK_TOKEN",
        "GEMINI_API_KEY",
        "GF_SECURITY_ADMIN_PASSWORD",
    ]

    for js_file in dist_dir.glob("*.js"):
        content = js_file.read_text(encoding="utf-8", errors="replace")
        for pattern in sensitive_patterns:
            assert pattern not in content, (
                f"Secret pattern '{pattern}' detected in bundle {js_file.name}!"
            )
