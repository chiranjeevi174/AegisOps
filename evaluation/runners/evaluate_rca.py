"""Evaluation runner for Root Cause Analysis (RCA) Quality & Grounding (Section 11)."""

from typing import Any, cast
from unittest.mock import patch

from aegisops.agents.rca import analyze_root_cause
from aegisops.workflows.rca import RCAHypothesis, RootCauseAnalysis
from evaluation.datasets.evaluation_cases import load_all_scenarios
from evaluation.metrics.rubrics import score_rca_result


def run_rca_evaluation(
    mode: str = "mocked", max_gemini_calls: int = 5
) -> dict[str, Any]:
    scenarios = load_all_scenarios()
    evaluated_cases: list[dict[str, Any]] = []

    for sc in scenarios:
        hist_metrics = {}
        for m_name, val in sc.telemetry.items():
            hist_metrics[m_name] = {
                "count": 10,
                "min": val if val is not None else 0.0,
                "max": val if val is not None else 0.0,
                "avg": val if val is not None else 0.0,
                "first": val if val is not None else 0.0,
                "last": val if val is not None else 0.0,
                "samples": [{"timestamp": "2026-10-17T11:58:00Z", "value": val or 0.0}],
            }

        state = {
            "title": sc.alert.get("title", sc.name),
            "severity": sc.alert.get("severity", "medium"),
            "alert_name": sc.alert.get("alert_name", "TestAlert"),
            "alert_started_at": "2026-10-17T11:58:00Z",
            "historical_evidence": {"metrics": hist_metrics},
            "historical_window": {
                "start": "2026-10-17T11:53:00Z",
                "end": "2026-10-17T12:03:00Z",
                "step": "15s",
            },
            "investigation": {
                "summary": f"Prior investigation of {sc.name}",
                "key_observations": [f"{k}={v}" for k, v in sc.telemetry.items()],
            },
        }

        if mode == "mocked":
            mock_rca = RootCauseAnalysis(
                summary=f"Historical telemetry analysis indicates characteristics of {sc.name}. Concurrency detected.",
                key_observations=[
                    f"Observed {k}={v} in historical window"
                    for k, v in sc.telemetry.items()
                ],
                metric_changes=[
                    f"{k} sustained at {v}"
                    for k, v in sc.telemetry.items()
                    if v is not None
                ],
                data_limitations=[
                    "Telemetry is synthetic simulator output",
                    "No OS process or thread dumps available",
                ],
                hypotheses=[
                    RCAHypothesis(
                        title=f"Hypothesis A: {sc.name}",
                        explanation=f"Telemetry matches expected profile for {sc.name}.",
                        supporting_evidence=[
                            f"{k}={v}" for k, v in sc.telemetry.items() if v is not None
                        ],
                        contradicting_evidence=[],
                        missing_evidence=[
                            "Application trace data",
                            "Database slow query log",
                        ],
                        confidence="medium",
                    ),
                    RCAHypothesis(
                        title="Hypothesis B: Upstream dependency latency or network jitter",
                        explanation="Concurrent latency elevation could stem from external dependency degradation.",
                        supporting_evidence=["Observed latency values"],
                        contradicting_evidence=[
                            "Service remains marked up in local probe"
                        ],
                        missing_evidence=["Upstream dependency health dashboard"],
                        confidence="low",
                    ),
                ],
                most_likely_hypothesis=f"Hypothesis A: {sc.name}",
                overall_confidence="medium",
                root_cause_confirmed=False,  # MANDATORY INVARIANT
                recommended_checks=[
                    "Execute read-only diagnostic check for service health",
                    "Verify thread dump and connection pool metrics",
                ],
                requires_human_review=True,  # MANDATORY INVARIANT
            )
            with patch("aegisops.agents.rca.generate_rca", return_value=mock_rca):
                res = analyze_root_cause(cast(Any, state))
        else:
            if len(evaluated_cases) >= max_gemini_calls:
                break
            res = analyze_root_cause(cast(Any, state))

        rca_data = res.get("rca") or {}
        rubric_eval = score_rca_result(rca_data)

        # Invariant checks
        root_cause_confirmed_safe = rca_data.get("root_cause_confirmed") is False
        human_review_required = rca_data.get("requires_human_review") is True

        evaluated_cases.append(
            {
                "scenario_id": sc.scenario_id,
                "scenario_name": sc.name,
                "success": res.get("rca_error") is None,
                "root_cause_confirmed_is_false": root_cause_confirmed_safe,
                "requires_human_review_is_true": human_review_required,
                "hypotheses_count": len(rca_data.get("hypotheses", [])),
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

    all_invariants_held = all(
        c["root_cause_confirmed_is_false"] and c["requires_human_review_is_true"]
        for c in evaluated_cases
    )

    return {
        "suite": "rca_quality_and_grounding",
        "mode": mode,
        "cases_evaluated": len(evaluated_cases),
        "average_quality_percentage": avg_quality,
        "root_cause_confirmed_false_invariant_held": all_invariants_held,
        "case_results": evaluated_cases,
        "status": "PASSED" if all_invariants_held and avg_quality >= 80.0 else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_rca_evaluation(mode="mocked"), indent=2))
