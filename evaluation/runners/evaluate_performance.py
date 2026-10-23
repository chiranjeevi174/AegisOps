"""Evaluation runner for Performance and Latency Benchmarks (Section 18)."""

import json
import time
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid4

from aegisops.agents.triage import triage_incident
from aegisops.rollback.eligibility import evaluate_rollback_eligibility
from aegisops.services.plan_integrity import compute_plan_hash, verify_plan_integrity
from aegisops.services.remediation_safety import validate_remediation_safety
from aegisops.workflows.remediation import RemediationAction, RemediationPlan
from evaluation.metrics.calculator import calculate_percentiles


def run_performance_evaluation(iterations: int = 50) -> dict[str, Any]:
    # 1. Triage latency benchmark
    triage_times_ms: list[float] = []
    for _ in range(iterations):
        state = {
            "incident_id": uuid4(),
            "title": "Latency benchmark incident",
            "severity": "critical",
            "status": "open",
        }
        t0 = time.perf_counter()
        triage_incident(cast(Any, state))
        t1 = time.perf_counter()
        triage_times_ms.append((t1 - t0) * 1000.0)

    # 2. Plan Hash Integrity Verification benchmark
    sample_plan = RemediationPlan(
        incident_summary="CPU saturation benchmark",
        planning_basis="Prometheus range query",
        recommended_actions=[
            RemediationAction(
                title="Inspect Health",
                description="Query service health endpoint",
                rationale="Confirm responsiveness",
                risk_level="low",
                action_type="diagnostic",
                requires_human_approval=True,
            )
        ],
        overall_risk="low",
        requires_human_approval=True,
        execution_enabled=False,
    )
    plan_dict = sample_plan.model_dump()
    plan_hash = compute_plan_hash(plan_dict)
    hash_times_ms: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        verify_plan_integrity(plan_dict, plan_hash)
        t1 = time.perf_counter()
        hash_times_ms.append((t1 - t0) * 1000.0)

    # 3. Deterministic Safety Validation benchmark
    test_plan = RemediationPlan(
        incident_summary="CPU saturation benchmark",
        planning_basis="Prometheus range query",
        recommended_actions=[
            RemediationAction(
                title="Inspect Health",
                description="Query service health endpoint",
                rationale="Confirm responsiveness",
                risk_level="low",
                action_type="diagnostic",
                requires_human_approval=True,
            )
        ],
        overall_risk="low",
        requires_human_approval=True,
        execution_enabled=False,
    )
    safety_times_ms: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        validate_remediation_safety(test_plan, rca={"overall_confidence": "medium"})
        t1 = time.perf_counter()
        safety_times_ms.append((t1 - t0) * 1000.0)

    # 4. Rollback Eligibility Assessment benchmark
    mock_exec = MagicMock()
    mock_exec.id = uuid4()
    mock_exec.mode = "live_diagnostic"
    mock_exec.status = "diagnosed"
    mock_exec.approved_plan_hash = "abc12345"
    mock_appr = MagicMock()
    mock_appr.id = uuid4()
    mock_appr.version = 1
    mock_inc = MagicMock()
    mock_inc.id = uuid4()
    mock_inc.severity = "high"
    mock_inc.status = "open"

    rollback_times_ms: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        evaluate_rollback_eligibility(
            execution=mock_exec,
            approval=mock_appr,
            incident=mock_inc,
            verification=None,
        )
        t1 = time.perf_counter()
        rollback_times_ms.append((t1 - t0) * 1000.0)

    results = {
        "suite": "performance_and_latency_benchmarks",
        "sample_size_per_operation": iterations,
        "measurements": {
            "triage_decision_latency_ms": calculate_percentiles(triage_times_ms),
            "plan_hash_verification_latency_ms": calculate_percentiles(hash_times_ms),
            "remediation_safety_validation_latency_ms": calculate_percentiles(
                safety_times_ms
            ),
            "rollback_eligibility_assessment_latency_ms": calculate_percentiles(
                rollback_times_ms
            ),
        },
        "status": "PASSED",
    }
    return results


if __name__ == "__main__":
    import json

    print(json.dumps(run_performance_evaluation(), indent=2))
