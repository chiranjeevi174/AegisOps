from typing import Literal

from pydantic import BaseModel, Field


class InvestigationResult(BaseModel):
    summary: str = Field(min_length=1)
    observations: list[str]
    possible_causes: list[str]
    recommended_checks: list[str]

    confidence: Literal["low", "medium", "high"]

    requires_human_review: bool = True
