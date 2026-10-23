from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RemediationAction(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"]
    action_type: Literal[
        "observation",
        "diagnostic",
        "configuration_review",
        "operational_change",
    ]
    validation_steps: list[str] = Field(default_factory=list)
    rollback_considerations: list[str] = Field(default_factory=list)
    requires_human_approval: bool = Field(default=True)

    @field_validator("requires_human_approval")
    @classmethod
    def validate_action_approval(cls, v: bool) -> bool:
        if v is False:
            raise ValueError("Human approval is mandatory for all remediation actions")
        return True


class RemediationPlan(BaseModel):
    incident_summary: str = Field(min_length=1)
    planning_basis: str = Field(min_length=1)
    recommended_actions: list[RemediationAction] = Field(min_length=1, max_length=5)
    missing_information: list[str] = Field(default_factory=list)
    overall_risk: Literal["low", "medium", "high"]
    requires_human_approval: bool = Field(default=True)
    execution_enabled: bool = Field(default=False)

    @field_validator("requires_human_approval")
    @classmethod
    def validate_plan_approval(cls, v: bool) -> bool:
        if v is False:
            raise ValueError("Human approval is mandatory for all remediation plans")
        return True

    @field_validator("execution_enabled")
    @classmethod
    def validate_execution_disabled(cls, v: bool) -> bool:
        if v is True:
            raise ValueError(
                "Execution cannot be enabled; remediation planning is advisory only"
            )
        return False
