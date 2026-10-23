from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from aegisops.domain.verification import VerificationOutcome


class VerificationCriteria(BaseModel):
    baseline_window_minutes: int = Field(
        default=15,
        ge=1,
        le=120,
        description="Historical baseline window duration in minutes preceding execution.",
    )
    followup_window_minutes: int = Field(
        default=15,
        ge=1,
        le=120,
        description="Follow-up monitoring observation window duration in minutes following execution.",
    )
    min_samples_required: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum sample observations required for statistically meaningful comparison.",
    )
    step: str = Field(
        default="15s",
        pattern=r"^\d+[smh]$",
        description="Prometheus range query resolution step.",
    )
    allowed_latency_increase_pct: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Allowable latency deviation threshold percentage before triggering degradation.",
    )
    allowed_error_rate_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Permissible HTTP error rate ceiling threshold.",
    )
    min_coverage_pct: float = Field(
        default=20.0,
        ge=1.0,
        le=100.0,
        description="Minimum temporal coverage percentage required across the observation window.",
    )
    max_allowed_gap_seconds: int = Field(
        default=300,
        ge=15,
        le=3600,
        description="Maximum permitted temporal gap between consecutive telemetry samples in seconds.",
    )


class MetricObservation(BaseModel):
    metric_name: str
    expression: str
    unit: str
    sample_count: int
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    latest_value: float | None = None
    is_retrospective: bool = False
    interval_start: datetime
    interval_end: datetime
    data_availability: Literal[
        "available", "no_data", "insufficient_samples", "insufficient_coverage", "error"
    ]
    label: str = "metric_observation"
    coverage_pct: float | None = None
    first_sample_time: datetime | None = None
    last_sample_time: datetime | None = None
    max_gap_seconds: float | None = None
    coverage_assessment: str | None = None


class MetricComparisonResult(BaseModel):
    metric_name: str
    unit: str
    baseline_mean: float | None = None
    followup_mean: float | None = None
    absolute_change: float | None = None
    relative_change_pct: float | None = None
    direction: Literal[
        "improved", "degraded", "unchanged", "insufficient_evidence", "undetermined"
    ]
    sample_sufficiency: bool
    evaluation_notes: list[str] = Field(default_factory=list)


class PostExecutionVerificationResult(BaseModel):
    execution_id: UUID
    incident_id: UUID
    approval_id: UUID
    operation_id: str
    execution_mode: str
    outcome: VerificationOutcome
    baseline_summary: MetricObservation | None = None
    followup_summary: MetricObservation | None = None
    comparison: MetricComparisonResult | None = None
    criteria: VerificationCriteria
    limitations: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    verified_at: datetime
    human_review_required: bool = Field(default=True)
    remediation_success_confirmed: bool = Field(default=False)

    @field_validator("remediation_success_confirmed")
    @classmethod
    def validate_remediation_success_confirmed(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError(
                "remediation_success_confirmed must strictly remain False for read-only post-execution verifications"
            )
        return False

    @field_validator("human_review_required")
    @classmethod
    def validate_human_review_required(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError(
                "human_review_required must strictly remain True for post-execution verifications"
            )
        return True
