"""Evaluation runner for Failure Recovery and Reliability (Section 17)."""

from typing import Any, cast
from unittest.mock import patch

from aegisops.agents.investigation import investigate_incident
from aegisops.agents.rca import analyze_root_cause
from aegisops.integrations.gemini import GeminiError
from aegisops.integrations.prometheus import PrometheusError
from aegisops.workflows.incident import incident_workflow


def run_reliability_evaluation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. Prometheus unreachable failure handling
    with patch(
        "aegisops.agents.evidence.collect_metrics",
        side_effect=PrometheusError("Connection refused"),
    ):
        state = {
            "title": "Prometheus down test",
            "alert_name": "TargetHighCPU",
            "severity": "critical",
            "status": "open",
        }
        res = incident_workflow.invoke(cast(Any, state))
        prom_error_handled = (
            res.get("monitoring_error") is not None
            and "Connection refused" in str(res.get("monitoring_error"))
            and res.get("investigation") is None
        )
        checks.append(
            {
                "id": "REL-001",
                "name": "Prometheus unreachable graceful handling",
                "passed": prom_error_handled,
            }
        )

    # 2. Gemini API quota / connection failure handling in Investigation
    with patch(
        "aegisops.agents.investigation.generate_investigation",
        side_effect=GeminiError("429 Quota Exceeded"),
    ):
        state = {
            "title": "Gemini 429 test",
            "severity": "high",
            "status": "open",
            "evidence": {"cpu_percent": 95.0},
        }
        inv_res = investigate_incident(cast(Any, state))
        gemini_inv_handled = inv_res.get(
            "investigation"
        ) is None and "429 Quota Exceeded" in str(inv_res.get("investigation_error"))
        checks.append(
            {
                "id": "REL-002",
                "name": "Gemini API 429 quota failure in investigation handled",
                "passed": gemini_inv_handled,
            }
        )

    # 3. Gemini API failure in RCA handling
    with patch(
        "aegisops.agents.rca.generate_rca",
        side_effect=GeminiError("500 Internal LLM Error"),
    ):
        rca_state = {
            "title": "RCA Gemini 500 test",
            "severity": "high",
            "historical_evidence": {"metrics": {"cpu_percent": {"samples": []}}},
        }
        rca_res = analyze_root_cause(cast(Any, rca_state))
        gemini_rca_handled = rca_res.get(
            "rca"
        ) is None and "500 Internal LLM Error" in str(rca_res.get("rca_error"))
        checks.append(
            {
                "id": "REL-003",
                "name": "Gemini API 500 internal error in RCA handled",
                "passed": gemini_rca_handled,
            }
        )

    # 4. Partial monitoring telemetry handling
    state_partial = {
        "title": "Partial metrics test",
        "severity": "medium",
        "evidence": {"cpu_percent": 80.0, "latency_seconds": None, "error_rate": None},
    }
    with patch("aegisops.agents.investigation.generate_investigation") as mock_inv:
        from aegisops.workflows.investigation import InvestigationResult

        mock_inv.return_value = InvestigationResult(
            summary="Partial metrics investigation",
            observations=["cpu_percent is 80%"],
            possible_causes=["CPU load"],
            recommended_checks=["Inspect health"],
            confidence="medium",
        )
        partial_res = investigate_incident(cast(Any, state_partial))
        checks.append(
            {
                "id": "REL-004",
                "name": "Partial monitoring telemetry handled without failure",
                "passed": partial_res.get("investigation_error") is None,
            }
        )

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    pass_rate = round((passed_count / total_count) * 100.0, 2)

    return {
        "suite": "failure_recovery_and_reliability",
        "checks_evaluated": total_count,
        "checks_passed": passed_count,
        "checks_failed": total_count - passed_count,
        "pass_rate_pct": pass_rate,
        "details": checks,
        "status": "PASSED" if passed_count == total_count else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_reliability_evaluation(), indent=2))
