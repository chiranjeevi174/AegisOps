from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.approval_event import ApprovalEventType
from aegisops.domain.incident import Incident
from aegisops.services import approvals
from aegisops.services.approvals import (
    ApprovalExpiredError,
    ApprovalValidationError,
    InvalidApprovalStateError,
    SelfApprovalError,
)
from aegisops.services.incidents import IncidentNotFoundError
from aegisops.services.plan_integrity import (
    PlanIntegrityError,
    compute_plan_hash,
    verify_plan_integrity,
)
from aegisops.workflows.remediation import RemediationAction, RemediationPlan

pytestmark = pytest.mark.asyncio


def sample_valid_plan(
    title: str = "Review JVM Garbage Collection Settings",
    action_type: str = "configuration_review",
    risk_level: str = "low",
) -> RemediationPlan:
    return RemediationPlan(
        incident_summary="Periodic high latency observed with CPU contention.",
        planning_basis="RCA medium confidence hypothesis on GC pauses.",
        recommended_actions=[
            RemediationAction(
                title=title,
                description="Inspect JVM GC pause telemetry and heap occupancy.",
                rationale="GC pauses correlate with cyclical latency peaks.",
                supporting_evidence=["Historical latency reached 4.2s"],
                prerequisites=["Access to JVM metrics"],
                risk_level=risk_level,  # pyright: ignore[reportArgumentType]
                action_type=action_type,  # pyright: ignore[reportArgumentType]
                validation_steps=["Verify heap headroom and GC pause frequency"],
                rollback_considerations=["No rollback required for diagnostic review"],
                requires_human_approval=True,
            )
        ],
        missing_information=["Thread dumps", "GC log files"],
        overall_risk="low",
        requires_human_approval=True,
        execution_enabled=False,
    )


async def create_test_incident(session_factory) -> Incident:
    incident_id = uuid4()
    async with session_factory() as session:
        incident = Incident(
            id=incident_id,
            title="High API latency detected",
            description="API latency spike detected by Alertmanager.",
            severity="high",
            status="open",
            source="alertmanager",
            alert_fingerprint=f"fp-{incident_id}",
            alert_started_at=datetime.now(UTC),
        )
        session.add(incident)
        await session.commit()
        await session.refresh(incident)
    return incident


# =========================================================================
# 1. Database & Service Level Tests
# =========================================================================


async def test_create_approval_request_success(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    plan = sample_valid_plan()
    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=plan,
            requested_by="sre-engineer-alice",
            validity_minutes=120,
            rca={"overall_confidence": "medium"},
        )

        assert approval.id is not None
        assert approval.incident_id == incident.id
        assert approval.status == ApprovalStatus.PENDING.value
        assert approval.version == 1
        assert approval.requested_by == "sre-engineer-alice"
        assert approval.decided_by is None
        assert approval.decided_at is None
        assert approval.plan_hash == compute_plan_hash(plan)
        assert approval.expires_at > datetime.now(UTC)

        # Verify initial audit event
        events = await approvals.get_approval_events(session, approval.id)
        assert len(events) == 1
        assert events[0].event_type == ApprovalEventType.CREATED.value
        assert events[0].new_status == ApprovalStatus.PENDING.value
        assert events[0].actor == "sre-engineer-alice"
        assert events[0].plan_hash == approval.plan_hash


async def test_create_approval_rejects_nonexistent_incident(test_context):
    _, session_factory = test_context
    non_existent_id = uuid4()

    async with session_factory() as session:
        with pytest.raises(IncidentNotFoundError):
            await approvals.create_approval_request(
                session=session,
                incident_id=non_existent_id,
                plan=sample_valid_plan(),
                requested_by="sre-engineer-alice",
            )


async def test_create_approval_supersedes_existing_pending_request(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        # Version 1
        appr1 = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(title="Initial recommendation"),
            requested_by="sre-engineer-alice",
        )
        assert appr1.version == 1
        assert appr1.status == ApprovalStatus.PENDING.value

        # Version 2 for the same incident
        appr2 = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(title="Revised recommendation"),
            requested_by="sre-engineer-alice",
        )
        assert appr2.version == 2
        assert appr2.status == ApprovalStatus.PENDING.value

        # Refresh v1
        reloaded_v1 = await session.get(RemediationApproval, appr1.id)
        assert reloaded_v1 is not None
        assert reloaded_v1.status == ApprovalStatus.SUPERSEDED.value

        # Verify audit trail for both
        events_v1 = await approvals.get_approval_events(session, appr1.id)
        assert len(events_v1) == 2
        assert events_v1[0].event_type == ApprovalEventType.CREATED.value
        assert events_v1[1].event_type == ApprovalEventType.SUPERSEDED.value

        events_v2 = await approvals.get_approval_events(session, appr2.id)
        assert len(events_v2) == 1
        assert events_v2[0].event_type == ApprovalEventType.CREATED.value


# =========================================================================
# 2. State Transition & Decision Tests
# =========================================================================


async def test_approve_request_lifecycle(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        decided = await approvals.approve_request(
            session=session,
            approval_id=approval.id,
            actor_identity="sre-lead-charlie",
            comment="Approved for diagnostic execution by SRE team.",
        )

        assert decided.status == ApprovalStatus.APPROVED.value
        assert decided.decided_by == "sre-lead-charlie"
        assert decided.decided_at is not None
        assert (
            decided.decision_reason == "Approved for diagnostic execution by SRE team."
        )

        # Audit event check
        events = await approvals.get_approval_events(session, approval.id)
        assert len(events) == 2
        assert events[1].event_type == ApprovalEventType.APPROVED.value
        assert events[1].actor == "sre-lead-charlie"
        assert events[1].new_status == ApprovalStatus.APPROVED.value


async def test_reject_request_lifecycle(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        decided = await approvals.reject_request(
            session=session,
            approval_id=approval.id,
            actor_identity="sre-lead-charlie",
            reason="Diagnostic steps are insufficient; thread dumps must be included.",
        )

        assert decided.status == ApprovalStatus.REJECTED.value
        assert decided.decided_by == "sre-lead-charlie"
        assert "thread dumps must be included" in decided.decision_reason

        events = await approvals.get_approval_events(session, approval.id)
        assert len(events) == 2
        assert events[1].event_type == ApprovalEventType.REJECTED.value


async def test_request_revision_lifecycle(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        decided = await approvals.request_revision(
            session=session,
            approval_id=approval.id,
            actor_identity="sre-lead-charlie",
            reason="Please add specific GC flag validation criteria.",
        )

        assert decided.status == ApprovalStatus.REVISION_REQUESTED.value
        assert decided.decided_by == "sre-lead-charlie"

        events = await approvals.get_approval_events(session, approval.id)
        assert len(events) == 2
        assert events[1].event_type == ApprovalEventType.REVISION_REQUESTED.value


async def test_terminal_state_transitions_rejected(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        # Transition to approved
        await approvals.approve_request(
            session=session,
            approval_id=approval.id,
            actor_identity="sre-lead-charlie",
        )

        # Attempt to approve again
        with pytest.raises(
            InvalidApprovalStateError,
            match="Cannot approve request in 'approved' status",
        ):
            await approvals.approve_request(
                session=session,
                approval_id=approval.id,
                actor_identity="sre-admin-bob",
            )

        # Attempt to reject an approved request
        with pytest.raises(
            InvalidApprovalStateError,
            match="Cannot reject request in 'approved' status",
        ):
            await approvals.reject_request(
                session=session,
                approval_id=approval.id,
                actor_identity="sre-admin-bob",
                reason="Changed mind",
            )


async def test_self_approval_prevention(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        # Requester tries to approve their own request
        with pytest.raises(SelfApprovalError, match="Self-approval prohibited"):
            await approvals.approve_request(
                session=session,
                approval_id=approval.id,
                actor_identity="sre-engineer-alice",
            )


async def test_rejection_requires_valid_reason(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        with pytest.raises(
            ApprovalValidationError, match="rejection reason is required"
        ):
            await approvals.reject_request(
                session=session,
                approval_id=approval.id,
                actor_identity="sre-lead-charlie",
                reason="  ",
            )


# =========================================================================
# 3. Expiration & Plan Integrity Tests
# =========================================================================


async def test_approval_dynamic_expiration(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        # Create approval that expired 1 minute ago
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
            validity_minutes=-1,
        )

        # Decision attempt should dynamically detect expiration and reject
        with pytest.raises(ApprovalExpiredError, match="has expired"):
            await approvals.approve_request(
                session=session,
                approval_id=approval.id,
                actor_identity="sre-lead-charlie",
            )

        # Verify status transitioned to expired
        reloaded = await session.get(RemediationApproval, approval.id)
        assert reloaded is not None
        assert reloaded.status == ApprovalStatus.EXPIRED.value


async def test_expire_stale_requests_batch_service(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
            validity_minutes=-5,
        )

        expired_count = await approvals.expire_stale_requests(session)
        assert expired_count == 1


async def test_plan_integrity_detection():
    plan = sample_valid_plan()
    h = compute_plan_hash(plan)

    snapshot = plan.model_dump(mode="json")
    assert verify_plan_integrity(snapshot, h) is True

    # Tamper with snapshot content
    tampered = dict(snapshot)
    tampered["incident_summary"] = "Tampered summary to bypass checks"
    assert verify_plan_integrity(tampered, h) is False

    # Tamper with execution_enabled
    tampered_exec = dict(snapshot)
    tampered_exec["execution_enabled"] = True
    assert (
        verify_plan_integrity(tampered_exec, compute_plan_hash(tampered_exec)) is False
    )


async def test_approve_rejects_tampered_plan(test_context):
    _, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

        # Tamper directly in database
        approval.plan_hash = (
            "0000000000000000000000000000000000000000000000000000000000000000"
        )
        await session.commit()

        with pytest.raises(PlanIntegrityError, match="integrity verification failed"):
            await approvals.approve_request(
                session=session,
                approval_id=approval.id,
                actor_identity="sre-lead-charlie",
            )


# =========================================================================
# 4. API Endpoints & Authentication Tests
# =========================================================================


async def test_api_unauthenticated_request_rejected(test_context):
    client, _ = test_context
    res = await client.get("/api/v1/approvals")
    assert res.status_code == 401


async def test_api_invalid_token_rejected(test_context):
    client, _ = test_context
    res = await client.get(
        "/api/v1/approvals",
        headers={"Authorization": "Bearer invalid-token-xyz"},
    )
    assert res.status_code == 401


async def test_api_insufficient_role_rejected(test_context):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async with session_factory() as session:
        approval = await approvals.create_approval_request(
            session=session,
            incident_id=incident.id,
            plan=sample_valid_plan(),
            requested_by="sre-engineer-alice",
        )

    # Viewer token tries to approve
    viewer_headers = {"Authorization": "Bearer aegisops-dev-viewer-token"}
    res = await client.post(
        f"/api/v1/approvals/{approval.id}/approve",
        headers=viewer_headers,
        json={"comment": "Trying to approve"},
    )
    assert res.status_code == 403
    assert "lacks approval permission" in res.json()["detail"]


async def test_api_full_approval_lifecycle(test_context, monkeypatch):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)

    # Mock workflow output for creation endpoint
    async def mock_run_incident_workflow(session, incident_id):
        return {
            "remediation_plan": sample_valid_plan().model_dump(mode="json"),
            "remediation_error": None,
            "rca": {"overall_confidence": "medium"},
        }

    monkeypatch.setattr(
        "aegisops.api.approvals.run_incident_workflow",
        mock_run_incident_workflow,
    )

    requester_headers = {"Authorization": "Bearer aegisops-dev-requester-token"}
    approver_headers = {"Authorization": "Bearer aegisops-dev-approver-token"}

    # 1. Create approval request
    create_res = await client.post(
        f"/api/v1/incidents/{incident.id}/approvals",
        headers=requester_headers,
    )
    assert create_res.status_code == 201
    approval_data = create_res.json()
    approval_id = approval_data["id"]
    assert approval_data["status"] == "pending"
    assert approval_data["version"] == 1
    assert approval_data["execution_enabled"] is False
    assert approval_data["requires_human_approval"] is True

    # 2. Get approval details
    get_res = await client.get(
        f"/api/v1/approvals/{approval_id}",
        headers=approver_headers,
    )
    assert get_res.status_code == 200
    assert "plan_snapshot" in get_res.json()

    # 3. Approve
    approve_res = await client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers=approver_headers,
        json={"comment": "Approved by lead"},
    )
    assert approve_res.status_code == 200
    decision = approve_res.json()
    assert decision["status"] == "approved"
    assert decision["decided_by"] == "sre-lead-charlie"
    assert decision["execution_enabled"] is False
    assert decision["requires_human_approval"] is True

    # 4. Verify audit events
    events_res = await client.get(
        f"/api/v1/approvals/{approval_id}/events",
        headers=approver_headers,
    )
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) == 2
    assert events[0]["event_type"] == "created"
    assert events[1]["event_type"] == "approved"

    # 5. Verify database incident was NOT modified
    async with session_factory() as session:
        db_incident = await session.get(Incident, incident.id)
        assert db_incident is not None
        assert db_incident.status == "open"


async def test_api_reject_and_request_revision(test_context, monkeypatch):
    client, session_factory = test_context
    incident = await create_test_incident(session_factory)

    async def mock_run_incident_workflow(session, incident_id):
        return {
            "remediation_plan": sample_valid_plan().model_dump(mode="json"),
            "remediation_error": None,
            "rca": {"overall_confidence": "medium"},
        }

    monkeypatch.setattr(
        "aegisops.api.approvals.run_incident_workflow",
        mock_run_incident_workflow,
    )

    requester_headers = {"Authorization": "Bearer aegisops-dev-requester-token"}
    approver_headers = {"Authorization": "Bearer aegisops-dev-approver-token"}

    # Create approval
    create_res = await client.post(
        f"/api/v1/incidents/{incident.id}/approvals",
        headers=requester_headers,
    )
    approval_id = create_res.json()["id"]

    # Reject with short reason (fails 422)
    bad_reject = await client.post(
        f"/api/v1/approvals/{approval_id}/reject",
        headers=approver_headers,
        json={"reason": "no"},
    )
    assert bad_reject.status_code == 422

    # Reject with valid reason
    good_reject = await client.post(
        f"/api/v1/approvals/{approval_id}/reject",
        headers=approver_headers,
        json={"reason": "Insufficient diagnostics provided for GC contention"},
    )
    assert good_reject.status_code == 200
    assert good_reject.json()["status"] == "rejected"
    assert good_reject.json()["execution_enabled"] is False
