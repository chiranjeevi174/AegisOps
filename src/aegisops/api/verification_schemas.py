from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from aegisops.verification.schemas import VerificationCriteria


class VerifyExecutionRequest(BaseModel):
    criteria: VerificationCriteria = Field(default_factory=VerificationCriteria)
    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        description="Unique caller-provided idempotency key for safely replaying or deduplicating requests.",
    )


class VerificationDetailResponse(BaseModel):
    id: UUID
    execution_id: UUID
    incident_id: UUID
    approval_id: UUID
    approved_plan_hash: str
    operation_id: str
    execution_mode: str
    status: str
    outcome: str
    verification_criteria: dict[str, Any]
    baseline_evidence: dict[str, Any] | None = None
    followup_evidence: dict[str, Any] | None = None
    metric_comparison: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    requested_by: str
    idempotency_key: str
    requested_at: datetime
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    human_review_required: bool
    remediation_success_confirmed: bool
    error_message: str | None = None
    is_replay: bool = False


class VerificationSummaryResponse(BaseModel):
    id: UUID
    execution_id: UUID
    incident_id: UUID
    approval_id: UUID
    operation_id: str
    execution_mode: str
    status: str
    outcome: str
    requested_by: str
    requested_at: datetime
    completed_at: datetime
    duration_ms: int
    human_review_required: bool
    remediation_success_confirmed: bool


class VerificationEventResponse(BaseModel):
    id: UUID
    verification_id: UUID
    execution_id: UUID
    actor: str
    event_type: str
    previous_status: str | None = None
    new_status: str
    outcome: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
