"""Evaluation runner for Post-Execution Verification and Rollback Readiness (Section 15)."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from aegisops.domain.execution import ExecutionMode, ExecutionStatus
from aegisops.domain.rollback import RollbackApplicability, RollbackReadinessStatus
from aegisops.domain.verification import VerificationOutcome
from aegisops.rollback.eligibility import evaluate_rollback_eligibility
from aegisops.rollback.schemas import RollbackReadinessAssessment
from aegisops.verification.schemas import (
    PostExecutionVerificationResult,
    VerificationCriteria,
)


def run_verifications_rollbacks_evaluation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. Verification schema invariants: remediation_success_confirmed must be False
    v_schema_pass = False
    try:
        PostExecutionVerificationResult(
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_service_health",
            execution_mode="live_diagnostic",
            outcome=VerificationOutcome.DIAGNOSTIC_VERIFIED,
            criteria=VerificationCriteria(),
            verified_at=datetime.now(UTC),
            remediation_success_confirmed=True,  # ATTACK: should fail validator
            human_review_required=True,
        )
    except ValueError:
        v_schema_pass = True

    checks.append(
        {
            "id": "VERIF-001",
            "name": "Verification schema forbids remediation_success_confirmed = True",
            "passed": v_schema_pass,
        }
    )

    # 2. Verification schema invariants: human_review_required must be True
    v_human_pass = False
    try:
        PostExecutionVerificationResult(
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_service_health",
            execution_mode="live_diagnostic",
            outcome=VerificationOutcome.DIAGNOSTIC_VERIFIED,
            criteria=VerificationCriteria(),
            verified_at=datetime.now(UTC),
            remediation_success_confirmed=False,
            human_review_required=False,  # ATTACK: should fail validator
        )
    except ValueError:
        v_human_pass = True

    checks.append(
        {
            "id": "VERIF-002",
            "name": "Verification schema mandates human_review_required = True",
            "passed": v_human_pass,
        }
    )

    # 3. Rollback schema invariants: rollback_execution_enabled must be False
    rb_exec_pass = False
    try:
        RollbackReadinessAssessment(
            assessment_id=uuid4(),
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_service_health",
            execution_mode="live_diagnostic",
            applicability="not_applicable",
            readiness_status="not_applicable",
            risk_level="low",
            rollback_execution_enabled=True,  # ATTACK: should fail validator
            human_authorization_required=True,
            system_changes_performed=False,
            assessed_at=datetime.now(UTC),
        )
    except ValueError:
        rb_exec_pass = True

    checks.append(
        {
            "id": "ROLLBACK-001",
            "name": "Rollback schema strictly enforces rollback_execution_enabled = False",
            "passed": rb_exec_pass,
        }
    )

    # 4. Rollback schema invariants: system_changes_performed must be False
    rb_sys_pass = False
    try:
        RollbackReadinessAssessment(
            assessment_id=uuid4(),
            execution_id=uuid4(),
            incident_id=uuid4(),
            approval_id=uuid4(),
            operation_id="inspect_service_health",
            execution_mode="live_diagnostic",
            applicability="not_applicable",
            readiness_status="not_applicable",
            risk_level="low",
            rollback_execution_enabled=False,
            human_authorization_required=True,
            system_changes_performed=True,  # ATTACK: should fail validator
            assessed_at=datetime.now(UTC),
        )
    except ValueError:
        rb_sys_pass = True

    checks.append(
        {
            "id": "ROLLBACK-002",
            "name": "Rollback schema strictly enforces system_changes_performed = False",
            "passed": rb_sys_pass,
        }
    )

    # 5. Truthful rollback evaluation for read-only live diagnostic
    mock_diag_exec = MagicMock()
    mock_diag_exec.id = uuid4()
    mock_diag_exec.mode = ExecutionMode.LIVE_DIAGNOSTIC.value
    mock_diag_exec.status = ExecutionStatus.DIAGNOSED.value
    mock_diag_exec.approved_plan_hash = "plan_hash_12345"

    mock_appr = MagicMock()
    mock_appr.id = uuid4()
    mock_appr.version = 1

    mock_inc = MagicMock()
    mock_inc.id = uuid4()
    mock_inc.severity = "high"
    mock_inc.status = "open"

    app_diag, status_diag, *_ = evaluate_rollback_eligibility(
        execution=mock_diag_exec,
        approval=mock_appr,
        incident=mock_inc,
        verification=None,
    )
    checks.append(
        {
            "id": "ROLLBACK-003",
            "name": "Live diagnostic correctly evaluated as Rollback: Not Applicable",
            "passed": app_diag == RollbackApplicability.NOT_APPLICABLE
            and status_diag == RollbackReadinessStatus.NOT_APPLICABLE,
        }
    )

    # 6. Truthful rollback evaluation for simulation
    mock_sim_exec = MagicMock()
    mock_sim_exec.id = uuid4()
    mock_sim_exec.mode = ExecutionMode.SIMULATION.value
    mock_sim_exec.status = ExecutionStatus.SIMULATED.value
    mock_sim_exec.approved_plan_hash = "plan_hash_12345"

    app_sim, status_sim, *_ = evaluate_rollback_eligibility(
        execution=mock_sim_exec,
        approval=mock_appr,
        incident=mock_inc,
        verification=None,
    )
    checks.append(
        {
            "id": "ROLLBACK-004",
            "name": "Simulation correctly evaluated as Rollback: Not Applicable",
            "passed": app_sim == RollbackApplicability.NOT_APPLICABLE
            and status_sim == RollbackReadinessStatus.NOT_APPLICABLE,
        }
    )

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    pass_rate = round((passed_count / total_count) * 100.0, 2)

    return {
        "suite": "verifications_and_rollbacks_safeguards",
        "checks_evaluated": total_count,
        "checks_passed": passed_count,
        "checks_failed": total_count - passed_count,
        "pass_rate_pct": pass_rate,
        "details": checks,
        "status": "PASSED" if passed_count == total_count else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_verifications_rollbacks_evaluation(), indent=2))
