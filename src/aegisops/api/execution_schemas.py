from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from aegisops.domain.execution import ExecutionMode, ExecutionStatus


class SimulateExecutionRequest(BaseModel):
    approval_id: UUID
    incident_id: UUID
    operation_id: str = Field(min_length=1, max_length=100)
    recommendation_index: int = Field(
        ge=1,
        description="1-based index of the approved recommendation this operation supports",
    )
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=128)


class DiagnoseExecutionRequest(BaseModel):
    approval_id: UUID
    incident_id: UUID
    operation_id: str = Field(min_length=1, max_length=100)
    recommendation_index: int = Field(
        ge=1,
        description="1-based index of the approved recommendation this operation supports",
    )
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ExecutionResponse(BaseModel):
    id: UUID
    incident_id: UUID
    approval_id: UUID
    approved_plan_hash: str
    approved_plan_version: int
    selected_recommendation_index: int
    selected_recommendation_title: str
    operation_id: str
    parameters: dict[str, Any]
    requested_by: str
    mode: ExecutionMode
    status: ExecutionStatus
    idempotency_key: str
    requested_at: datetime
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    is_replay: bool = False
    actual_infrastructure_access: bool = False
    system_changes_performed: bool = False

    model_config = {"from_attributes": True}


class ExecutionDetailResponse(ExecutionResponse):
    simulation_result: dict[str, Any] | None = None
    diagnostic_result: dict[str, Any] | None = None


class ExecutionEventResponse(BaseModel):
    id: UUID
    execution_id: UUID
    incident_id: UUID
    approval_id: UUID
    actor: str
    event_type: str
    previous_status: str | None = None
    new_status: str
    operation_id: str
    approved_plan_hash: str
    details: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class AllowlistedOperationResponse(BaseModel):
    id: str
    name: str
    description: str
    risk_level: str
    required_permission: str
    max_simulated_duration_ms: int
    real_execution_supported: bool = False
    live_diagnostic_supported: bool = False
    supported_modes: list[str] = Field(default_factory=lambda: ["simulation"])
    is_read_only: bool = True
    parameters_schema: dict[str, Any]
