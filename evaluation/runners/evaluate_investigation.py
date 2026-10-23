"""Evaluation runner for Gemini Investigation Quality (Section 10)."""

from typing import Any, cast
from unittest.mock import patch

from aegisops.agents.investigation import investigate_incident
from aegisops.workflows.investigation import InvestigationResult
from evaluation.datasets.evaluation_cases import load_all_scenarios
from evaluation.metrics.rubrics import score_investigation_result


def run_investigation_evaluation(
    mode: str = "mocked", max_gemini_calls: int = 5
) -> dict[str, Any]:
    scenarios = load_all_scenarios()
    evaluated_cases: list[dict[str, Any]] = []

    for sc in scenarios:
        state = {
            "title": sc.alert.get("title", sc.name),
            "severity": sc.alert.get("severity", "medium"),
            "alert_name": sc.alert.get("alert_name", "TestAlert"),
            "evidence": sc.telemetry,
            "evidence_type": "synthetic_snapshot",
            "evidence_collected_at": "2026-10-17T12:00:00Z",
            "alert_started_at": "2026-10-17T11:58:00Z",
        }

        if mode == "mocked":
            # Deterministic, grounded mock structured response
            obs = [
                f"cpu_percent is {sc.telemetry.get('cpu_percent')}%",
                f"latency_seconds is {sc.telemetry.get('latency_seconds')}s",
                f"error_rate is {sc.telemetry.get('error_rate')}",
                f"service_up is {sc.telemetry.get('service_up')}",
            ]
            mock_investigation = InvestigationResult(
                summary=f"Synthetic telemetry investigation for {sc.name}. Anomaly detected: {sc.expected.get('is_anomalous')}.",
                observations=obs,
                possible_causes=[
                    f"Possible scenario cause: {sc.name}",
                    "External client traffic surge",
                ],
                recommended_checks=[
                    "Inspect service health check endpoint",
                    "Query Prometheus historical range query for 15m window",
                ],
                confidence="high" if not sc.expected.get("is_anomalous") else "medium",
                requires_human_review=True,
            )
            with patch(
                "aegisops.agents.investigation.generate_investigation",
                return_value=mock_investigation,
            ):
                res = investigate_incident(cast(Any, state))
        else:
            # Live mode with bounded calls
            if len(evaluated_cases) >= max_gemini_calls:
                break
            res = investigate_incident(cast(Any, state))

        inv_data = res.get("investigation") or {}
        rubric_eval = score_investigation_result(inv_data)

        evaluated_cases.append(
            {
                "scenario_id": sc.scenario_id,
                "scenario_name": sc.name,
                "success": res.get("investigation_error") is None,
                "error": res.get("investigation_error"),
                "rubric_scores": rubric_eval["scores"],
                "quality_percentage": rubric_eval["quality_percentage"],
                "details": rubric_eval["details"],
            }
        )

    avg_quality = (
        round(
            sum(c["quality_percentage"] for c in evaluated_cases)
            / len(evaluated_cases),
            2,
        )
        if evaluated_cases
        else 0.0
    )

    all_passed = all(
        c["success"] and c["quality_percentage"] >= 80.0 for c in evaluated_cases
    )

    return {
        "suite": "gemini_investigation_quality",
        "mode": mode,
        "cases_evaluated": len(evaluated_cases),
        "average_quality_percentage": avg_quality,
        "case_results": evaluated_cases,
        "status": "PASSED" if all_passed else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_investigation_evaluation(mode="mocked"), indent=2))
