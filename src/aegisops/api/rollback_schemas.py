from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateRollbackAssessmentRequest(BaseModel):
    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        description="Unique caller-provided idempotency key for safely replaying or deduplicating assessment requests.",
    )


class RollbackAssessmentDetailResponse(BaseModel):
    id: UUID
    execution_id: UUID
    incident_id: UUID
    approval_id: UUID
    approved_plan_hash: str
    operation_id: str
    execution_mode: str
    status: str
    readiness_status: str
    applicability: str
    risk_level: str
    assessment_data: dict[str, Any] = Field(default_factory=dict)
    simulation_result: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    requested_by: str
    idempotency_key: str
    requested_at: datetime
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    human_authorization_required: bool
    rollback_execution_enabled: bool
    system_changes_performed: bool
    error_message: str | None = None
    is_replay: bool = False


class RollbackAssessmentSummaryResponse(BaseModel):
    id: UUID
    execution_id: UUID
    incident_id: UUID
    approval_id: UUID
    operation_id: str
    execution_mode: str
    status: str
    readiness_status: str
    applicability: str
    risk_level: str
    requested_by: str
    requested_at: datetime
    completed_at: datetime
    duration_ms: int
    human_authorization_required: bool
    rollback_execution_enabled: bool
    system_changes_performed: bool


class RollbackEventResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    execution_id: UUID
    actor: str
    event_type: str
    previous_status: str | None = None
    new_status: str
    readiness_status: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
