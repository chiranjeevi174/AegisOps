from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AlertPayload(BaseModel):
    status: Literal["firing", "resolved"]
    fingerprint: str = Field(min_length=1, max_length=100)
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime | None = None


class AlertmanagerPayload(BaseModel):
    receiver: str
    status: Literal["firing", "resolved"]
    alerts: list[AlertPayload] = Field(min_length=1, max_length=100)
