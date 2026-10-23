"""Evaluation runner for deterministic Incident Triage logic (Section 8)."""

from typing import Any, cast
from uuid import uuid4

from aegisops.agents.triage import triage_incident
from aegisops.workflows.incident import incident_workflow


def run_triage_evaluation() -> dict[str, Any]:
    test_cases = [
        {"id": "TRIAGE-001", "severity": "critical", "exp_p": "P1", "exp_esc": True},
        {"id": "TRIAGE-002", "severity": "high", "exp_p": "P2", "exp_esc": True},
        {"id": "TRIAGE-003", "severity": "medium", "exp_p": "P3", "exp_esc": False},
        {"id": "TRIAGE-004", "severity": "low", "exp_p": "P4", "exp_esc": False},
        {"id": "TRIAGE-005", "severity": "CRITICAL", "exp_p": "P1", "exp_esc": True},
        {"id": "TRIAGE-006", "severity": "High", "exp_p": "P2", "exp_esc": True},
        {"id": "TRIAGE-007", "severity": None, "exp_p": "P3", "exp_esc": False},
        {
            "id": "TRIAGE-008",
            "severity": "unknown_sev",
            "exp_p": "P3",
            "exp_esc": False,
        },
        {"id": "TRIAGE-009", "severity": "", "exp_p": "P3", "exp_esc": False},
    ]

    evaluated = 0
    correct = 0
    failed_cases: list[dict[str, Any]] = []

    for tc in test_cases:
        evaluated += 1
        state = {
            "incident_id": uuid4(),
            "title": f"Test Incident {tc['id']}",
            "severity": tc["severity"],
            "status": "open",
        }
        res = triage_incident(cast(Any, state))
        p_ok = res.get("priority") == tc["exp_p"]
        esc_ok = res.get("requires_escalation") is tc["exp_esc"]

        if p_ok and esc_ok:
            correct += 1
        else:
            failed_cases.append(
                {
                    "case_id": tc["id"],
                    "input_severity": tc["severity"],
                    "expected": {"priority": tc["exp_p"], "escalation": tc["exp_esc"]},
                    "actual": res,
                }
            )

    # Workflow state propagation check
    state_prop_ok = True
    wf_state = {
        "incident_id": uuid4(),
        "title": "State propagation check",
        "severity": "critical",
        "status": "open",
    }
    wf_res = incident_workflow.invoke(cast(Any, wf_state))
    if (
        wf_res.get("priority") != "P1"
        or wf_res.get("requires_escalation") is not True
        or wf_res.get("incident_id") != wf_state["incident_id"]
    ):
        state_prop_ok = False

    accuracy = round((correct / evaluated) * 100.0, 2) if evaluated > 0 else 0.0

    return {
        "suite": "incident_triage",
        "cases_evaluated": evaluated,
        "correct_classifications": correct,
        "incorrect_classifications": len(failed_cases),
        "accuracy_pct": accuracy,
        "state_propagation_verified": state_prop_ok,
        "failed_case_identifiers": [c["case_id"] for c in failed_cases],
        "status": "PASSED" if correct == evaluated and state_prop_ok else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_triage_evaluation(), indent=2))
