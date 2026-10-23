from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from aegisops.domain.approval import ApprovalStatus


class ApproveRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class RevisionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class ApprovalResponse(BaseModel):
    id: UUID
    incident_id: UUID
    status: ApprovalStatus
    version: int
    plan_hash: str
    requested_by: str
    requested_at: datetime
    expires_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None
    requires_human_approval: bool = True
    execution_enabled: bool = False

    model_config = {"from_attributes": True}


class ApprovalDetailResponse(ApprovalResponse):
    plan_snapshot: dict[str, Any]


class ApprovalEventResponse(BaseModel):
    id: UUID
    approval_id: UUID
    incident_id: UUID
    actor: str
    event_type: str
    previous_status: str | None = None
    new_status: str
    reason: str | None = None
    plan_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionResponse(BaseModel):
    approval_id: UUID
    incident_id: UUID
    status: ApprovalStatus
    version: int
    plan_hash: str
    decided_by: str
    decided_at: datetime
    decision_reason: str | None = None
    requires_human_approval: bool = True
    execution_enabled: bool = False
