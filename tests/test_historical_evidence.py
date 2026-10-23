from datetime import UTC, datetime, timedelta

from aegisops.integrations.prometheus import MetricSample, PrometheusError
from aegisops.services.historical_evidence import collect_historical_metric_window


def test_collect_historical_window_construction(monkeypatch):
    captured_intervals = {}

    def mock_range(expression, start, end, step="15s"):
        captured_intervals[expression] = (start, end, step)
        return [
            MetricSample(timestamp=start, value=10.0),
            MetricSample(timestamp=end, value=20.0),
        ]

    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        mock_range,
    )

    alert_time = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)
    data = collect_historical_metric_window(
        alert_started_at=alert_time,
        window_before_minutes=5,
        window_after_minutes=5,
        step="15s",
    )

    expected_start = datetime(2026, 10, 15, 7, 5, tzinfo=UTC)
    expected_end = datetime(2026, 10, 15, 7, 15, tzinfo=UTC)

    assert data.window_start == expected_start
    assert data.window_end == expected_end
    assert data.step == "15s"


def test_collect_historical_future_window_clamped(monkeypatch):
    captured_intervals = []

    def mock_range(expression, start, end, step="15s"):
        captured_intervals.append((start, end))
        return []

    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        mock_range,
    )

    # Future alert time
    now_before = datetime.now(UTC)
    future_time = now_before + timedelta(minutes=10)

    data = collect_historical_metric_window(alert_started_at=future_time)
    now_after = datetime.now(UTC)

    # Clamped to current UTC time
    assert data.window_end <= now_after
    assert data.window_start < data.window_end


def test_statistical_aggregation_and_zero_values(monkeypatch):
    def mock_range(expression, start, end, step="15s"):
        if "cpu" in expression:
            return [
                MetricSample(timestamp=start, value=10.0),
                MetricSample(timestamp=start + timedelta(seconds=15), value=50.0),
                MetricSample(timestamp=start + timedelta(seconds=30), value=90.0),
            ]
        elif "error_rate" in expression:
            # Genuine 0.0 values must be preserved
            return [
                MetricSample(timestamp=start, value=0.0),
                MetricSample(timestamp=start + timedelta(seconds=15), value=0.0),
            ]
        else:
            return []

    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        mock_range,
    )

    alert_time = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    data = collect_historical_metric_window(alert_time)

    cpu = data.metrics["cpu_percent"]
    assert cpu.count == 3
    assert cpu.min == 10.0
    assert cpu.max == 90.0
    assert cpu.avg == 50.0
    assert cpu.first == 10.0
    assert cpu.last == 90.0

    # Genuine 0.0 value is not missing
    err = data.metrics["error_rate"]
    assert err.count == 2
    assert err.min == 0.0
    assert err.max == 0.0
    assert err.avg == 0.0
    assert err.first == 0.0
    assert err.last == 0.0

    # Empty metrics represented as missing evidence (None)
    lat = data.metrics["latency_seconds"]
    assert lat.count == 0
    assert lat.min is None
    assert lat.max is None
    assert lat.avg is None
    assert lat.first is None
    assert lat.last is None


def test_partial_metric_availability_and_failure_handling(monkeypatch):
    def mock_range(expression, start, end, step="15s"):
        if "cpu" in expression:
            return [MetricSample(timestamp=start, value=85.0)]
        else:
            raise PrometheusError("Prometheus connection timeout")

    monkeypatch.setattr(
        "aegisops.services.historical_evidence.query_prometheus_range",
        mock_range,
    )

    alert_time = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    data = collect_historical_metric_window(alert_time)

    assert data.metrics["cpu_percent"].count == 1
    assert data.metrics["cpu_percent"].avg == 85.0
    assert "cpu_percent" not in data.errors

    # Failing metrics are recorded in errors dict
    assert "latency_seconds" in data.errors
    assert data.metrics["latency_seconds"].count == 0
    assert data.metrics["latency_seconds"].min is None
