from typing import Literal

from pydantic import BaseModel, Field


class RCAHypothesis(BaseModel):
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]


class RootCauseAnalysis(BaseModel):
    summary: str = Field(min_length=1)
    key_observations: list[str] = Field(default_factory=list)
    metric_changes: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)

    hypotheses: list[RCAHypothesis] = Field(default_factory=list)

    most_likely_hypothesis: str | None = None
    overall_confidence: Literal["low", "medium", "high"]
    root_cause_confirmed: bool = Field(default=False)
    recommended_checks: list[str] = Field(default_factory=list)
    requires_human_review: bool = Field(default=True)
