from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    severity: Literal["critical", "high", "medium", "low"]


class IncidentResponse(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: Literal["open", "investigating", "resolved"]
    source: str
    created_at: datetime
    alert_fingerprint: str | None = None
    alert_state: str | None = None
    alert_started_at: datetime | None = None
    alert_updated_at: datetime | None = None
