import pytest

pytestmark = pytest.mark.asyncio


async def test_auth_actors_endpoint(test_context):
    client, _ = test_context
    res = await client.get("/api/v1/auth/actors")
    assert res.status_code == 200
    actors = res.json()
    assert isinstance(actors, list)
    identities = [a["identity"] for a in actors]
    assert "sre-operator-dan" in identities
    assert "sre-lead-charlie" in identities


async def test_auth_session_and_me(test_context):
    client, _ = test_context
    # Invalid login
    res = await client.post("/api/v1/auth/session", json={"token": "invalid-token"})
    assert res.status_code == 401

    # Valid login using development identity switcher
    res = await client.post(
        "/api/v1/auth/session", json={"identity": "sre-operator-dan"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["identity"] == "sre-operator-dan"
    assert "operator" in data["roles"]
    assert data["can_execute"] is True
    assert "aegisops_session" in res.cookies

    # Test /api/v1/auth/me using the cookie
    client.cookies.set("aegisops_session", res.cookies["aegisops_session"])
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["identity"] == "sre-operator-dan"

    # Test logout with CSRF token
    csrf_token = data.get("csrf_token") or res.cookies.get("aegisops_csrf")
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token or "", "Origin": "http://testserver"},
    )
    assert logout_res.status_code == 200

    # Clear client cookie and test me without cookie should be 401
    client.cookies.delete("aegisops_session")
    me_after = await client.get("/api/v1/auth/me")
    assert me_after.status_code == 401


async def test_auth_me_bearer(test_context):
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["identity"] == "sre-operator-dan"


async def test_system_overview_endpoint(test_context):
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    res = await client.get("/api/v1/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_incidents" in data
    assert "open_incidents" in data
    assert "incidents_by_severity" in data
    assert "pending_approvals" in data
    assert "total_executions" in data
    assert "grafana_url" in data


async def test_system_settings_endpoint(test_context):
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    res = await client.get("/api/v1/system/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["app_name"] == "AegisOps"
    assert data["environment"] == "development"
    assert "current_actor" in data


async def test_audit_events_endpoint(test_context):
    client, _ = test_context
    headers = {"Authorization": "Bearer aegisops-dev-operator-token"}
    res = await client.get("/api/v1/audit/events", headers=headers)
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
