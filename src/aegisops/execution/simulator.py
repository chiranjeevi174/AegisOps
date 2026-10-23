from typing import Any

from aegisops.execution.registry import (
    get_operation_definition,
    validate_operation_parameters,
)
from aegisops.execution.schemas import SimulationResult


def simulate_operation(
    operation_id: str,
    raw_parameters: dict[str, Any] | None = None,
) -> SimulationResult:
    """Simulates an allowlisted diagnostic operation without accessing real infrastructure or performing mutations."""
    op_def = get_operation_definition(operation_id)
    validated_params = validate_operation_parameters(operation_id, raw_parameters or {})

    if operation_id == "inspect_service_health":
        service = validated_params.get("service_name", "api-service")
        include_deps = validated_params.get("include_dependencies", True)
        return SimulationResult(
            operation_id=operation_id,
            mode="simulation",
            parameters=validated_params,
            intended_purpose="Simulate probing service availability, uptime indicators, and readiness endpoints.",
            target_scope=f"Service: {service} (dependencies: {include_deps})",
            expected_observations=[
                f"Verify HTTP 200 on /{service}/health and /ready endpoints",
                "Check Prometheus up indicator metric",
                "Evaluate upstream and downstream dependency status",
            ],
            risk_assessment="Low risk read-only diagnostic simulation. Zero operational side effects.",
            actual_infrastructure_access=False,
            system_changes_performed=False,
            dry_run=True,
            status="simulated_success",
            simulated_output={
                "check_type": "read_only_health_probe",
                "target_service": service,
                "simulated_checks": [
                    "liveness_probe",
                    "readiness_probe",
                    "dependency_ping",
                ],
                "note": "Simulation mode: no network requests or container probes executed.",
            },
        )

    if operation_id == "inspect_cpu_metrics":
        window = validated_params.get("window_minutes", 15)
        step = validated_params.get("step", "15s")
        return SimulationResult(
            operation_id=operation_id,
            mode="simulation",
            parameters=validated_params,
            intended_purpose="Simulate evaluating CPU utilization patterns and container throttling telemetry.",
            target_scope=f"Prometheus query range: last {window}m (step: {step})",
            expected_observations=[
                "Examine container CPU usage seconds rate over evaluation window",
                "Inspect CPU CFS quota throttled periods percentage",
                "Correlate core saturation with alert occurrence timestamp",
            ],
            risk_assessment="Low risk read-only metric evaluation simulation.",
            actual_infrastructure_access=False,
            system_changes_performed=False,
            dry_run=True,
            status="simulated_success",
            simulated_output={
                "query_type": "range_telemetry_simulation",
                "simulated_promql": f"rate(container_cpu_usage_seconds_total[{step}])",
                "window_minutes": window,
                "note": "Simulation mode: queries mapped without external network I/O.",
            },
        )

    if operation_id == "inspect_latency_metrics":
        window = validated_params.get("window_minutes", 15)
        step = validated_params.get("step", "15s")
        return SimulationResult(
            operation_id=operation_id,
            mode="simulation",
            parameters=validated_params,
            intended_purpose="Simulate evaluating API response duration distributions and percentile trends.",
            target_scope=f"Prometheus query range: last {window}m (step: {step})",
            expected_observations=[
                "Calculate p50, p90, and p99 duration histogram percentiles",
                "Isolate routes exhibiting response degradation exceeding SLA",
                "Correlate duration surge intervals with concurrent request rate",
            ],
            risk_assessment="Low risk read-only metric evaluation simulation.",
            actual_infrastructure_access=False,
            system_changes_performed=False,
            dry_run=True,
            status="simulated_success",
            simulated_output={
                "query_type": "range_telemetry_simulation",
                "simulated_promql": f"histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[{step}])) by (le))",
                "window_minutes": window,
                "note": "Simulation mode: queries mapped without external network I/O.",
            },
        )

    if operation_id == "inspect_error_rate":
        window = validated_params.get("window_minutes", 15)
        step = validated_params.get("step", "15s")
        return SimulationResult(
            operation_id=operation_id,
            mode="simulation",
            parameters=validated_params,
            intended_purpose="Simulate evaluating HTTP 5xx error rate ratios and status code distributions.",
            target_scope=f"Prometheus query range: last {window}m (step: {step})",
            expected_observations=[
                "Calculate 5xx error percentage against total traffic volume",
                "Isolate top failing endpoint routes and error codes",
                "Identify sudden error burst transitions",
            ],
            risk_assessment="Low risk read-only metric evaluation simulation.",
            actual_infrastructure_access=False,
            system_changes_performed=False,
            dry_run=True,
            status="simulated_success",
            simulated_output={
                "query_type": "range_telemetry_simulation",
                "simulated_promql": f"sum(rate(http_requests_total{{status=~'5..' }}[{step}])) / sum(rate(http_requests_total[{step}]))",
                "window_minutes": window,
                "note": "Simulation mode: queries mapped without external network I/O.",
            },
        )

    if operation_id == "review_service_configuration":
        component = validated_params.get("component", "runtime-configuration")
        return SimulationResult(
            operation_id=operation_id,
            mode="simulation",
            parameters=validated_params,
            intended_purpose="Simulate a read-only configuration review of runtime flags and memory thresholds.",
            target_scope=f"Component: {component}",
            expected_observations=[
                "Verify heap boundaries (-Xmx, -Xms) and GC collector flags",
                "Inspect worker thread pool and connection pool maximums",
                "Audit request timeout thresholds and queue capacity limits",
            ],
            risk_assessment="Low risk read-only configuration audit simulation.",
            actual_infrastructure_access=False,
            system_changes_performed=False,
            dry_run=True,
            status="simulated_success",
            simulated_output={
                "audit_type": "read_only_config_simulation",
                "component": component,
                "simulated_checks": [
                    "heap_allocations",
                    "thread_limits",
                    "connection_pools",
                ],
                "note": "Simulation mode: static schema audit without system configuration mutations.",
            },
        )

    raise ValueError(f"Unhandled allowlisted operation: {op_def.id}")
