"""Evaluation runner for Historical Evidence Accuracy (Section 9)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

from aegisops.integrations.prometheus import (
    MetricSample,
    PrometheusError,
    query_prometheus_range,
)
from aegisops.services.historical_evidence import (
    collect_historical_metric_window,
)


def run_historical_evidence_evaluation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. Timezone-awareness requirement
    naive_dt = datetime(2026, 10, 17, 12, 0, 0)
    try:
        collect_historical_metric_window(naive_dt)
        checks.append(
            {"id": "HIST-001", "name": "Naive timestamp rejection", "passed": False}
        )
    except ValueError:
        checks.append(
            {"id": "HIST-001", "name": "Naive timestamp rejection", "passed": True}
        )

    # 2. Window clamping to now
    future_alert = datetime.now(UTC) + timedelta(minutes=60)
    window = collect_historical_metric_window(
        future_alert, window_before_minutes=10, window_after_minutes=10
    )
    now = datetime.now(UTC)
    # window_end should be clamped to <= now
    clamped_ok = window.window_end <= now + timedelta(seconds=2)
    checks.append(
        {"id": "HIST-002", "name": "Future window clamping", "passed": clamped_ok}
    )

    # 3. Genuine zero value preservation
    zero_samples = [
        MetricSample(timestamp=datetime.now(UTC) - timedelta(seconds=30), value=0.0),
        MetricSample(timestamp=datetime.now(UTC) - timedelta(seconds=15), value=0.0),
    ]
    with patch(
        "aegisops.services.historical_evidence.query_prometheus_range",
        return_value=zero_samples,
    ):
        res = collect_historical_metric_window(datetime.now(UTC) - timedelta(minutes=5))
        cpu_stat = res.metrics.get("cpu_percent")
        zero_preserved = (
            cpu_stat is not None
            and cpu_stat.min == 0.0
            and cpu_stat.max == 0.0
            and cpu_stat.avg == 0.0
            and cpu_stat.count == 2
        )
        checks.append(
            {
                "id": "HIST-003",
                "name": "Genuine zero value preservation",
                "passed": zero_preserved,
            }
        )

    # 4. Non-finite value rejection
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "cpu"},
                        "values": [["1760000000", "NaN"]],
                    }
                ],
            },
        }
        try:
            query_prometheus_range(
                "cpu",
                datetime.now(UTC) - timedelta(minutes=5),
                datetime.now(UTC),
            )
            checks.append(
                {
                    "id": "HIST-004",
                    "name": "Non-finite value (NaN/Inf) rejection",
                    "passed": False,
                }
            )
        except PrometheusError:
            checks.append(
                {
                    "id": "HIST-004",
                    "name": "Non-finite value (NaN/Inf) rejection",
                    "passed": True,
                }
            )

    # 5. Missing series handling (empty matrix)
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "success",
            "data": {"resultType": "matrix", "result": []},
        }
        samples = query_prometheus_range(
            "missing_metric",
            datetime.now(UTC) - timedelta(minutes=5),
            datetime.now(UTC),
        )
        checks.append(
            {
                "id": "HIST-005",
                "name": "Missing series returns empty list",
                "passed": samples == [],
            }
        )

    # 6. Statistical calculation accuracy
    known_samples = [
        MetricSample(timestamp=datetime.now(UTC) - timedelta(seconds=60), value=10.0),
        MetricSample(timestamp=datetime.now(UTC) - timedelta(seconds=45), value=20.0),
        MetricSample(timestamp=datetime.now(UTC) - timedelta(seconds=30), value=30.0),
        MetricSample(timestamp=datetime.now(UTC) - timedelta(seconds=15), value=40.0),
    ]
    with patch(
        "aegisops.services.historical_evidence.query_prometheus_range",
        return_value=known_samples,
    ):
        res = collect_historical_metric_window(datetime.now(UTC) - timedelta(minutes=5))
        cpu_stat = res.metrics.get("cpu_percent")
        stats_correct = (
            cpu_stat is not None
            and cpu_stat.min == 10.0
            and cpu_stat.max == 40.0
            and cpu_stat.avg == 25.0
            and cpu_stat.first == 10.0
            and cpu_stat.last == 40.0
            and cpu_stat.count == 4
        )
        checks.append(
            {
                "id": "HIST-006",
                "name": "Statistical summary accuracy (min/max/avg/first/last)",
                "passed": stats_correct,
            }
        )

    # 7. Start time must be strictly before end time
    t0 = datetime.now(UTC)
    try:
        query_prometheus_range("cpu", t0, t0 - timedelta(seconds=10))
        checks.append(
            {"id": "HIST-007", "name": "Inverted interval rejection", "passed": False}
        )
    except ValueError:
        checks.append(
            {"id": "HIST-007", "name": "Inverted interval rejection", "passed": True}
        )

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    pass_rate = round((passed_count / total_count) * 100.0, 2)

    return {
        "suite": "historical_evidence_accuracy",
        "checks_evaluated": total_count,
        "checks_passed": passed_count,
        "checks_failed": total_count - passed_count,
        "pass_rate_pct": pass_rate,
        "details": checks,
        "status": "PASSED" if passed_count == total_count else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_historical_evidence_evaluation(), indent=2))
