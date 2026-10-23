import math
from datetime import UTC, datetime

import requests
from pydantic import BaseModel

from aegisops.core.config import get_settings

QUERIES = {
    "cpu_percent": "aegisops_sim_cpu_usage_percent",
    "latency_seconds": "aegisops_sim_latency_seconds",
    "error_rate": "aegisops_sim_error_rate",
    "service_up": "aegisops_sim_service_up",
}


class MetricSample(BaseModel):
    timestamp: datetime
    value: float


class PrometheusError(Exception):
    """Raised when monitoring evidence cannot be retrieved."""


def query_prometheus(
    expression: str,
    at: datetime | None = None,
) -> float | None:
    if at is not None and at.utcoffset() is None:
        raise ValueError("Evaluation timestamp must be timezone-aware")

    url = f"{get_settings().prometheus_url.rstrip('/')}/api/v1/query"
    params: dict[str, str | float] = {"query": expression}
    if at is not None:
        params["time"] = at.timestamp()

    try:
        response = requests.get(
            url,
            params=params,
            timeout=5,
        )
        response.raise_for_status()

        payload = response.json()

        if payload.get("status") != "success":
            raise PrometheusError("Prometheus query was unsuccessful")

        results = payload["data"]["result"]

        if not results:
            return None

        if len(results) != 1:
            raise PrometheusError("Expected exactly one metric series")

        return float(results[0]["value"][1])

    except PrometheusError:
        raise
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        raise PrometheusError("Failed to retrieve Prometheus evidence") from exc


def query_prometheus_range(
    expression: str,
    start: datetime,
    end: datetime,
    step: str = "15s",
) -> list[MetricSample]:
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("Evaluation timestamps must be timezone-aware")
    if start >= end:
        raise ValueError("Start time must be strictly before end time")

    url = f"{get_settings().prometheus_url.rstrip('/')}/api/v1/query_range"
    params: dict[str, str | float] = {
        "query": expression,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=5,
        )
        response.raise_for_status()

        payload = response.json()

        if payload.get("status") != "success":
            raise PrometheusError("Prometheus range query was unsuccessful")

        results = payload.get("data", {}).get("result", [])

        if not results:
            return []

        if len(results) != 1:
            raise PrometheusError("Expected exactly one metric series")

        raw_values = results[0].get("values", [])
        samples: list[MetricSample] = []

        for item in raw_values:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise PrometheusError("Invalid metric sample format")

            ts = float(item[0])
            val = float(item[1])

            if not math.isfinite(val):
                raise PrometheusError(f"Invalid non-finite metric value: {val}")

            samples.append(
                MetricSample(
                    timestamp=datetime.fromtimestamp(ts, tz=UTC),
                    value=val,
                )
            )

        return samples

    except PrometheusError:
        raise
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        raise PrometheusError("Failed to retrieve Prometheus range evidence") from exc


def collect_metrics(
    at: datetime | None = None,
) -> dict[str, float | None]:
    return {
        name: query_prometheus(expression, at=at)
        for name, expression in QUERIES.items()
    }
