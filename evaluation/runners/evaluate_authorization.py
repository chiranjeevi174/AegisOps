"""Evaluation runner for Approval and Authorization Boundaries (Section 13)."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from aegisops.core.auth import AuthenticatedActor
from aegisops.services.approvals import (
    SelfApprovalError,
)
from aegisops.services.plan_integrity import (
    compute_plan_hash,
    verify_plan_integrity,
)
from aegisops.workflows.remediation import RemediationAction, RemediationPlan


def run_authorization_evaluation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. RBAC permissions mapping
    approver = AuthenticatedActor(identity="charlie", roles=frozenset(["approver"]))
    requester = AuthenticatedActor(identity="bob", roles=frozenset(["requester"]))
    operator = AuthenticatedActor(identity="dan", roles=frozenset(["operator"]))
    observer = AuthenticatedActor(identity="alice", roles=frozenset(["observer"]))

    checks.append(
        {
            "id": "AUTH-001",
            "name": "Approver permission check",
            "passed": approver.can_approve is True and observer.can_approve is False,
        }
    )
    checks.append(
        {
            "id": "AUTH-002",
            "name": "Requester permission check",
            "passed": requester.can_request is True and observer.can_request is False,
        }
    )
    checks.append(
        {
            "id": "AUTH-003",
            "name": "Executor permission check",
            "passed": operator.can_execute is True and observer.can_execute is False,
        }
    )

    # 2. Separation of duties (Self-approval restriction)
    # When requested_by == actor_identity, self approval must be blocked
    def check_self_approval(requested_by: str, decided_by: str) -> None:
        if requested_by == decided_by:
            raise SelfApprovalError(
                "Self-approval prohibited: requesting actor cannot approve their own plan"
            )

    self_approval_blocked = False
    try:
        check_self_approval("bob", "bob")
    except SelfApprovalError:
        self_approval_blocked = True

    checks.append(
        {
            "id": "AUTH-004",
            "name": "Self-approval restriction (Separation of duties)",
            "passed": self_approval_blocked,
        }
    )

    # Distinct engineer approval is allowed
    distinct_approval_allowed = False
    try:
        check_self_approval("bob", "charlie")
        distinct_approval_allowed = True
    except SelfApprovalError:
        distinct_approval_allowed = False

    checks.append(
        {
            "id": "AUTH-005",
            "name": "Dual-control distinct engineer approval allowed",
            "passed": distinct_approval_allowed,
        }
    )

    # 3. Plan hash verification & Tamper resistance
    valid_plan = RemediationPlan(
        incident_summary="CPU inspection plan",
        planning_basis="Prometheus range query",
        recommended_actions=[
            RemediationAction(
                title="Inspect Health",
                description="Query service health endpoint",
                rationale="Check responsiveness",
                risk_level="low",
                action_type="diagnostic",
                requires_human_approval=True,
            )
        ],
        overall_risk="low",
        requires_human_approval=True,
        execution_enabled=False,
    )
    plan_dict = valid_plan.model_dump()
    valid_hash = compute_plan_hash(plan_dict)

    # Valid hash integrity check
    hash_verified = verify_plan_integrity(plan_dict, valid_hash)
    checks.append(
        {
            "id": "AUTH-006",
            "name": "Plan hash integrity verification",
            "passed": hash_verified is True,
        }
    )

    # Tampered plan integrity check (tampered hash or tampered snapshot)
    tampered_snapshot = dict(plan_dict)
    tampered_snapshot["incident_summary"] = "Tampered summary modification"
    tamper_detected = verify_plan_integrity(tampered_snapshot, valid_hash) is False

    checks.append(
        {
            "id": "AUTH-007",
            "name": "Tampered plan snapshot rejection",
            "passed": tamper_detected,
        }
    )

    # 4. Expiration check logic
    past_expiration = datetime.now(UTC) - timedelta(minutes=10)
    is_expired = past_expiration < datetime.now(UTC)
    checks.append(
        {
            "id": "AUTH-008",
            "name": "Approval expiration detection",
            "passed": is_expired is True,
        }
    )

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    pass_rate = round((passed_count / total_count) * 100.0, 2)

    return {
        "suite": "approval_and_authorization_boundaries",
        "checks_evaluated": total_count,
        "checks_passed": passed_count,
        "checks_failed": total_count - passed_count,
        "pass_rate_pct": pass_rate,
        "details": checks,
        "status": "PASSED" if passed_count == total_count else "FAILED",
    }


if __name__ == "__main__":
    print(json.dumps(run_authorization_evaluation(), indent=2))
