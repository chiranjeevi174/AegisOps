from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RollbackPrerequisite(BaseModel):
    name: str = Field(description="Identifier or title of the prerequisite condition.")
    description: str = Field(
        description="Detailed operational description of what is required."
    )
    satisfied: bool = Field(
        description="Whether the prerequisite condition is currently met."
    )
    details: str | None = Field(
        default=None, description="Additional context, telemetry, or reason."
    )


class RollbackStep(BaseModel):
    step_number: int = Field(
        ge=1, description="Sequential ordering of the advisory rollback step."
    )
    action_type: str = Field(
        description="Qualitative category of the step (e.g. advisory_reversion, telemetry_check)."
    )
    description: str = Field(
        description="Advisory operational instructions for human review."
    )
    target_component: str = Field(
        description="Service, subsystem, or component targeted by the step."
    )
    estimated_duration_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Estimated duration in seconds if executed by human operator.",
    )
    advisory_notes: list[str] = Field(
        default_factory=list, description="Safety considerations and warnings."
    )


class RollbackSimulationResult(BaseModel):
    simulation_mode: str = Field(
        default="simulation_only",
        description="Explicit identifier indicating dry-run simulation mode without infrastructure mutation.",
    )
    simulated_at: datetime = Field(
        description="UTC timestamp when the simulation was conducted."
    )
    can_safely_simulate: bool = Field(
        description="Whether the rollback plan can be evaluated safely in simulation."
    )
    simulated_actions: list[str] = Field(
        default_factory=list,
        description="Descriptive summary of actions modeled during simulation.",
    )
    simulated_target_state: str = Field(
        description="Hypothetical target state that would be achieved upon human authorization."
    )
    risk_assessment_summary: str = Field(
        description="Concise summary of operational risks evaluated during simulation."
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Evaluation notes, simulator caveats, and behavioral observations.",
    )


class RollbackReadinessAssessment(BaseModel):
    assessment_id: UUID = Field(
        description="Unique UUID of this rollback readiness assessment record."
    )
    execution_id: UUID = Field(
        description="UUID of the original completed execution being evaluated."
    )
    incident_id: UUID = Field(
        description="UUID of the incident associated with the execution."
    )
    approval_id: UUID = Field(description="UUID of the approved remediation plan.")
    operation_id: str = Field(
        description="Operation identifier of the original execution."
    )
    execution_mode: str = Field(
        description="Original execution mode (e.g. live_diagnostic, simulation)."
    )
    applicability: Literal["not_applicable", "applicable", "unsupported"] = Field(
        description="Whether rollback is applicable to the target operation."
    )
    readiness_status: Literal[
        "ready_for_review", "blocked", "insufficient_evidence", "not_applicable"
    ] = Field(description="Deterministic rollback readiness outcome.")
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Operational risk classification of hypothetical reversal."
    )
    prerequisites: list[RollbackPrerequisite] = Field(
        default_factory=list,
        description="List of required conditions and their satisfaction state.",
    )
    evidence_supporting_readiness: list[str] = Field(
        default_factory=list,
        description="Facts and monitoring evidence supporting this assessment.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Gaps in evidence, telemetry, or state knowledge.",
    )
    proposed_steps: list[RollbackStep] = Field(
        default_factory=list,
        description="Descriptive advisory steps for human operator review.",
    )
    validation_criteria: list[str] = Field(
        default_factory=list,
        description="Telemetry and health criteria required after hypothetical rollback.",
    )
    human_authorization_required: bool = Field(
        default=True,
        description="Mandatory invariant: human authorization is always required before rollback.",
    )
    rollback_execution_enabled: bool = Field(
        default=False,
        description="Mandatory invariant: automatic rollback execution is strictly disabled.",
    )
    system_changes_performed: bool = Field(
        default=False,
        description="Mandatory invariant: confirms zero infrastructure modifications occurred.",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Explicit constraints, telemetry caveats, or read-only boundaries.",
    )
    observations: list[str] = Field(
        default_factory=list,
        description="Diagnostic findings and assessment summary observations.",
    )
    simulation_result: RollbackSimulationResult | None = Field(
        default=None,
        description="Structured simulation output if simulation was conducted.",
    )
    assessed_at: datetime = Field(
        description="UTC timestamp when this assessment was generated."
    )

    @field_validator("rollback_execution_enabled")
    @classmethod
    def validate_rollback_execution_enabled(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError(
                "rollback_execution_enabled must strictly remain False (rollback execution is disabled)"
            )
        return False

    @field_validator("human_authorization_required")
    @classmethod
    def validate_human_authorization_required(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError(
                "human_authorization_required must strictly remain True (human review is mandatory)"
            )
        return True

    @field_validator("system_changes_performed")
    @classmethod
    def validate_system_changes_performed(cls, v: bool) -> bool:
        if v is not False:
            raise ValueError(
                "system_changes_performed must strictly remain False (no infrastructure changes performed)"
            )
        return False
