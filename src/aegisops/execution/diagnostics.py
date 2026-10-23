import math
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from aegisops.execution.registry import (
    OperationNotAllowedError,
    validate_operation_parameters,
)
from aegisops.integrations.prometheus import (
    PrometheusError,
    query_prometheus,
    query_prometheus_range,
)


class DiagnosticMetricSummary(BaseModel):
    sample_count: int
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    latest_value: float | None = None
    unit: str


class LiveDiagnosticResult(BaseModel):
    operation_id: str
    execution_mode: str = "live_diagnostic"
    metric_identifier: str
    query_interval: dict[str, Any]
    collected_at: datetime
    data_availability_status: Literal["available", "no_data", "error"]
    actual_infrastructure_access: bool = True
    system_changes_performed: bool = False
    summary: DiagnosticMetricSummary | None = None
    measurements: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)


# Server-defined fixed PromQL mapping for live diagnostic operations
DIAGNOSTIC_METRICS: dict[str, dict[str, str]] = {
    "inspect_service_health": {
        "expression": "aegisops_sim_service_up",
        "unit": "binary",
        "label": "Service Availability",
    },
    "inspect_cpu_metrics": {
        "expression": "aegisops_sim_cpu_usage_percent",
        "unit": "%",
        "label": "CPU Utilization",
    },
    "inspect_latency_metrics": {
        "expression": "aegisops_sim_latency_seconds",
        "unit": "s",
        "label": "API Response Latency",
    },
    "inspect_error_rate": {
        "expression": "aegisops_sim_error_rate",
        "unit": "ratio",
        "label": "HTTP Error Rate",
    },
}


def _diagnose_service_health(params: dict[str, Any]) -> LiveDiagnosticResult:
    now = datetime.now(UTC)
    metric_info = DIAGNOSTIC_METRICS["inspect_service_health"]
    expression = metric_info["expression"]
    unit = metric_info["unit"]
    service_name = params.get("service_name", "api-service")

    instant_val = query_prometheus(expression, at=now)

    query_interval = {
        "type": "instant",
        "evaluation_time": now.isoformat(),
        "service_name": service_name,
    }

    if instant_val is None:
        return LiveDiagnosticResult(
            operation_id="inspect_service_health",
            metric_identifier=expression,
            query_interval=query_interval,
            collected_at=now,
            data_availability_status="no_data",
            actual_infrastructure_access=True,
            system_changes_performed=False,
            summary=None,
            measurements=[],
            observations=[
                f"No Prometheus metric samples returned for service '{service_name}' ({expression})"
            ],
        )

    # instant_val could be 0.0 or 1.0; both are valid measurements
    is_up = instant_val >= 1.0
    status_str = "UP" if is_up else "DOWN"

    summary = DiagnosticMetricSummary(
        sample_count=1,
        min_value=instant_val,
        max_value=instant_val,
        mean_value=instant_val,
        latest_value=instant_val,
        unit=unit,
    )

    measurement = {
        "timestamp": now.isoformat(),
        "value": instant_val,
        "status": status_str,
    }

    return LiveDiagnosticResult(
        operation_id="inspect_service_health",
        metric_identifier=expression,
        query_interval=query_interval,
        collected_at=now,
        data_availability_status="available",
        actual_infrastructure_access=True,
        system_changes_performed=False,
        summary=summary,
        measurements=[measurement],
        observations=[
            f"Live service availability for '{service_name}' is {status_str} (metric value: {instant_val})"
        ],
    )


def _diagnose_range_metric(
    operation_id: str,
    params: dict[str, Any],
) -> LiveDiagnosticResult:
    metric_info = DIAGNOSTIC_METRICS[operation_id]
    expression = metric_info["expression"]
    unit = metric_info["unit"]
    label = metric_info["label"]

    now = datetime.now(UTC)
    window_minutes = int(params.get("window_minutes", 15))
    window_minutes = max(1, min(120, window_minutes))
    step = str(params.get("step", "15s"))

    start = now - timedelta(minutes=window_minutes)
    end = now

    query_interval = {
        "type": "range",
        "window_minutes": window_minutes,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "step": step,
    }

    samples = query_prometheus_range(
        expression=expression,
        start=start,
        end=end,
        step=step,
    )

    if not samples:
        return LiveDiagnosticResult(
            operation_id=operation_id,
            metric_identifier=expression,
            query_interval=query_interval,
            collected_at=now,
            data_availability_status="no_data",
            actual_infrastructure_access=True,
            system_changes_performed=False,
            summary=None,
            measurements=[],
            observations=[
                f"No metric samples returned from Prometheus for {label} ({expression}) over the last {window_minutes}m"
            ],
        )

    values = [s.value for s in samples]
    finite_values = [v for v in values if math.isfinite(v)]
    if not finite_values:
        raise PrometheusError(f"No finite numerical values in {expression} range query")

    min_val = round(min(finite_values), 4)
    max_val = round(max(finite_values), 4)
    mean_val = round(sum(finite_values) / len(finite_values), 4)
    latest_val = round(finite_values[-1], 4)

    summary = DiagnosticMetricSummary(
        sample_count=len(samples),
        min_value=min_val,
        max_value=max_val,
        mean_value=mean_val,
        latest_value=latest_val,
        unit=unit,
    )

    measurements = [
        {
            "timestamp": s.timestamp.isoformat(),
            "value": s.value,
        }
        for s in samples
    ]

    observations = [
        f"Retrieved {len(samples)} actual Prometheus measurement(s) for {label}.",
        f"Window: last {window_minutes} minutes, Step: {step}.",
        f"Latest: {latest_val} {unit}, Mean: {mean_val} {unit}, Min: {min_val} {unit}, Max: {max_val} {unit}.",
    ]

    return LiveDiagnosticResult(
        operation_id=operation_id,
        metric_identifier=expression,
        query_interval=query_interval,
        collected_at=now,
        data_availability_status="available",
        actual_infrastructure_access=True,
        system_changes_performed=False,
        summary=summary,
        measurements=measurements,
        observations=observations,
    )


# Explicit handler dispatch mapping
DIAGNOSTIC_HANDLERS = {
    "inspect_service_health": _diagnose_service_health,
    "inspect_cpu_metrics": lambda p: _diagnose_range_metric("inspect_cpu_metrics", p),
    "inspect_latency_metrics": lambda p: _diagnose_range_metric(
        "inspect_latency_metrics", p
    ),
    "inspect_error_rate": lambda p: _diagnose_range_metric("inspect_error_rate", p),
}


def execute_diagnostic_operation(
    operation_id: str,
    raw_params: dict[str, Any],
) -> LiveDiagnosticResult:
    """Dispatches and executes a verified read-only diagnostic against Prometheus."""
    handler = DIAGNOSTIC_HANDLERS.get(operation_id)
    if handler is None:
        raise OperationNotAllowedError(
            f"Operation '{operation_id}' does not support live diagnostics"
        )

    validated_params = validate_operation_parameters(operation_id, raw_params)
    return handler(validated_params)
