from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field


class ServiceHealthParams(BaseModel):
    service_name: str = Field(default="api-service", max_length=50)
    include_dependencies: bool = Field(default=True)


class MetricInspectionParams(BaseModel):
    window_minutes: int = Field(default=15, ge=1, le=120)
    step: str = Field(default="15s", pattern=r"^[0-9]+[smhd]$")


class ConfigReviewParams(BaseModel):
    component: str = Field(default="runtime-configuration", max_length=50)
    include_runtime_flags: bool = Field(default=True)


@dataclass(frozen=True)
class OperationDefinition:
    id: str
    name: str
    description: str
    risk_level: Literal["low", "medium", "high"]
    required_permission: str
    parameters_schema: type[BaseModel]
    max_simulated_duration_ms: int
    real_execution_supported: bool = False
    live_diagnostic_supported: bool = False
    supported_modes: frozenset[str] = frozenset(["simulation"])
    is_read_only: bool = True
    max_window_minutes: int = 120
    timeout_seconds: int = 5


# Fixed, immutable server-side allowlist
ALLOWLISTED_OPERATIONS: dict[str, OperationDefinition] = {
    "inspect_service_health": OperationDefinition(
        id="inspect_service_health",
        name="Inspect Service Health",
        description="Inspect service availability, uptime indicators, and health check endpoints.",
        risk_level="low",
        required_permission="execute:diagnostic",
        parameters_schema=ServiceHealthParams,
        max_simulated_duration_ms=5000,
        real_execution_supported=False,
        live_diagnostic_supported=True,
        supported_modes=frozenset(["simulation", "live_diagnostic"]),
        is_read_only=True,
        max_window_minutes=120,
        timeout_seconds=5,
    ),
    "inspect_cpu_metrics": OperationDefinition(
        id="inspect_cpu_metrics",
        name="Inspect CPU Metrics",
        description="Inspect CPU telemetry, core allocation, and CPU throttling trends.",
        risk_level="low",
        required_permission="execute:diagnostic",
        parameters_schema=MetricInspectionParams,
        max_simulated_duration_ms=5000,
        real_execution_supported=False,
        live_diagnostic_supported=True,
        supported_modes=frozenset(["simulation", "live_diagnostic"]),
        is_read_only=True,
        max_window_minutes=120,
        timeout_seconds=5,
    ),
    "inspect_latency_metrics": OperationDefinition(
        id="inspect_latency_metrics",
        name="Inspect Latency Metrics",
        description="Inspect API latency distributions and duration trends.",
        risk_level="low",
        required_permission="execute:diagnostic",
        parameters_schema=MetricInspectionParams,
        max_simulated_duration_ms=5000,
        real_execution_supported=False,
        live_diagnostic_supported=True,
        supported_modes=frozenset(["simulation", "live_diagnostic"]),
        is_read_only=True,
        max_window_minutes=120,
        timeout_seconds=5,
    ),
    "inspect_error_rate": OperationDefinition(
        id="inspect_error_rate",
        name="Inspect Error Rate Metrics",
        description="Inspect HTTP error rate spikes, status codes, and error percentage ratios.",
        risk_level="low",
        required_permission="execute:diagnostic",
        parameters_schema=MetricInspectionParams,
        max_simulated_duration_ms=5000,
        real_execution_supported=False,
        live_diagnostic_supported=True,
        supported_modes=frozenset(["simulation", "live_diagnostic"]),
        is_read_only=True,
        max_window_minutes=120,
        timeout_seconds=5,
    ),
    "review_service_configuration": OperationDefinition(
        id="review_service_configuration",
        name="Review Service Configuration",
        description="Read-only configuration audit of JVM/runtime flags, thread pools, and memory limits (simulation-only).",
        risk_level="low",
        required_permission="execute:diagnostic",
        parameters_schema=ConfigReviewParams,
        max_simulated_duration_ms=5000,
        real_execution_supported=False,
        live_diagnostic_supported=False,
        supported_modes=frozenset(["simulation"]),
        is_read_only=True,
        max_window_minutes=120,
        timeout_seconds=5,
    ),
}

# Explicitly banned patterns and names
BANNED_OPERATION_NAMES = frozenset(
    [
        "run_command",
        "execute_script",
        "shell",
        "custom_action",
        "run_python",
        "execute_sql",
        "bash",
        "powershell",
        "cmd",
    ]
)


class OperationNotAllowedError(Exception):
    """Raised when an operation is not in the allowlist or is forbidden."""


def get_operation_definition(operation_id: str) -> OperationDefinition:
    """Retrieves an operation definition from the static allowlist, failing closed if unrecognized."""
    if operation_id in BANNED_OPERATION_NAMES:
        raise OperationNotAllowedError(
            f"Operation '{operation_id}' is explicitly forbidden"
        )

    op = ALLOWLISTED_OPERATIONS.get(operation_id)
    if op is None:
        raise OperationNotAllowedError(
            f"Operation '{operation_id}' is not in the remediation allowlist"
        )
    return op


def validate_operation_parameters(
    operation_id: str, raw_params: dict[str, Any]
) -> dict[str, Any]:
    """Validates raw parameters against the operation's specific Pydantic schema."""
    op = get_operation_definition(operation_id)
    validated = op.parameters_schema.model_validate(raw_params)
    return validated.model_dump(mode="json")
