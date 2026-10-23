from datetime import UTC, datetime

import pytest
import requests

from aegisops.integrations.prometheus import (
    MetricSample,
    PrometheusError,
    query_prometheus_range,
)


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_query_prometheus_range_success(monkeypatch):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": "cpu"},
                    "values": [
                        [1760511600, "50.5"],
                        [1760511615, "75.0"],
                    ],
                }
            ],
        },
    }

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, params, timeout: MockResponse(mock_payload),
    )

    samples = query_prometheus_range("cpu", start, end, step="15s")

    assert len(samples) == 2
    assert isinstance(samples[0], MetricSample)
    assert samples[0].value == 50.5
    assert samples[0].timestamp == datetime.fromtimestamp(1760511600, tz=UTC)
    assert samples[1].value == 75.0


def test_query_prometheus_range_empty_result(monkeypatch):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    mock_payload = {
        "status": "success",
        "data": {"resultType": "matrix", "result": []},
    }

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, params, timeout: MockResponse(mock_payload),
    )

    samples = query_prometheus_range("cpu", start, end)
    assert samples == []


def test_query_prometheus_range_multiple_series_rejected(monkeypatch):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {"metric": {"id": "1"}, "values": [[1760511600, "10"]]},
                {"metric": {"id": "2"}, "values": [[1760511600, "20"]]},
            ],
        },
    }

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, params, timeout: MockResponse(mock_payload),
    )

    with pytest.raises(PrometheusError, match="Expected exactly one metric series"):
        query_prometheus_range("cpu", start, end)


def test_query_prometheus_range_http_error(monkeypatch):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    def mock_get(url, params, timeout):
        raise requests.RequestException("Connection refused")

    monkeypatch.setattr(requests, "get", mock_get)

    with pytest.raises(
        PrometheusError, match="Failed to retrieve Prometheus range evidence"
    ):
        query_prometheus_range("cpu", start, end)


def test_query_prometheus_range_unsuccessful_status(monkeypatch):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    mock_payload = {"status": "error", "error": "bad query"}

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, params, timeout: MockResponse(mock_payload),
    )

    with pytest.raises(
        PrometheusError, match="Prometheus range query was unsuccessful"
    ):
        query_prometheus_range("cpu", start, end)


def test_query_prometheus_range_rejects_naive_timestamps():
    naive_start = datetime(2026, 10, 15, 7, 0)
    aware_end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    with pytest.raises(ValueError, match="must be timezone-aware"):
        query_prometheus_range("cpu", naive_start, aware_end)

    aware_start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    naive_end = datetime(2026, 10, 15, 7, 10)

    with pytest.raises(ValueError, match="must be timezone-aware"):
        query_prometheus_range("cpu", aware_start, naive_end)


def test_query_prometheus_range_rejects_invalid_interval():
    t1 = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)
    t2 = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="Start time must be strictly before end time"):
        query_prometheus_range("cpu", t1, t2)

    with pytest.raises(ValueError, match="Start time must be strictly before end time"):
        query_prometheus_range("cpu", t1, t1)


@pytest.mark.parametrize("bad_val", ["NaN", "Inf", "-Inf", "null", "invalid_number"])
def test_query_prometheus_range_rejects_invalid_numerical_values(monkeypatch, bad_val):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)

    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {},
                    "values": [[1760511600, bad_val]],
                }
            ],
        },
    }

    monkeypatch.setattr(
        requests,
        "get",
        lambda url, params, timeout: MockResponse(mock_payload),
    )

    with pytest.raises(PrometheusError):
        query_prometheus_range("cpu", start, end)


def test_query_prometheus_range_parameter_forwarding(monkeypatch):
    start = datetime(2026, 10, 15, 7, 0, tzinfo=UTC)
    end = datetime(2026, 10, 15, 7, 10, tzinfo=UTC)
    captured = {}

    def mock_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return MockResponse(
            {
                "status": "success",
                "data": {"resultType": "matrix", "result": []},
            }
        )

    monkeypatch.setattr(requests, "get", mock_get)

    query_prometheus_range("test_metric", start, end, step="30s")

    assert "/api/v1/query_range" in captured["url"]
    assert captured["params"]["query"] == "test_metric"
    assert captured["params"]["start"] == start.timestamp()
    assert captured["params"]["end"] == end.timestamp()
    assert captured["params"]["step"] == "30s"
    assert captured["timeout"] == 5
