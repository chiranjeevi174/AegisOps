from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegisops.domain.approval import RemediationApproval
from aegisops.domain.execution import (
    ExecutionMode,
    ExecutionStatus,
    RemediationExecution,
)
from aegisops.domain.incident import Incident
from aegisops.domain.rollback import (
    RollbackApplicability,
    RollbackReadinessStatus,
    RollbackRiskLevel,
)
from aegisops.domain.verification import ExecutionVerification
from aegisops.execution.registry import get_operation_definition
from aegisops.rollback.schemas import (
    RollbackPrerequisite,
    RollbackStep,
)
from aegisops.services.executions import ExecutionNotFoundError
from aegisops.services.plan_integrity import PlanIntegrityError


class RollbackEligibilityError(Exception):
    """Raised when an execution cannot be evaluated for rollback due to integrity or state violation."""


async def validate_execution_for_rollback_eligibility(
    session: AsyncSession,
    execution_id: UUID,
) -> tuple[
    RemediationExecution, RemediationApproval, Incident, ExecutionVerification | None
]:
    """Validates execution integrity, association, and terminal readiness before rollback evaluation."""
    execution = await session.get(RemediationExecution, execution_id)
    if not execution:
        raise ExecutionNotFoundError(
            f"Remediation execution '{execution_id}' does not exist"
        )

    approval = await session.get(RemediationApproval, execution.approval_id)
    if not approval:
        raise RollbackEligibilityError(
            f"Referenced approval '{execution.approval_id}' for execution does not exist"
        )

    incident = await session.get(Incident, execution.incident_id)
    if not incident:
        raise RollbackEligibilityError(
            f"Referenced incident '{execution.incident_id}' for execution does not exist"
        )

    if execution.approved_plan_hash != approval.plan_hash:
        raise PlanIntegrityError(
            "Security violation: Execution approved plan hash does not match approval plan hash"
        )

    # Validate registered operation
    get_operation_definition(execution.operation_id)

    # Terminal state check
    terminal_statuses = {
        ExecutionStatus.SIMULATED.value,
        ExecutionStatus.DIAGNOSED.value,
        ExecutionStatus.FAILED.value,
        ExecutionStatus.TIMED_OUT.value,
        ExecutionStatus.REJECTED.value,
    }
    if execution.status not in terminal_statuses:
        raise RollbackEligibilityError(
            f"Execution is not in a terminal state (current status: '{execution.status}'). "
            "Rollback assessment requires completed execution records."
        )

    # Optional verification record lookup
    v_query = (
        select(ExecutionVerification)
        .where(ExecutionVerification.execution_id == execution_id)
        .order_by(ExecutionVerification.requested_at.desc())
    )
    v_res = await session.execute(v_query)
    verification = v_res.scalars().first()

    return execution, approval, incident, verification


def evaluate_rollback_eligibility(
    execution: RemediationExecution,
    approval: RemediationApproval,
    incident: Incident,
    verification: ExecutionVerification | None,
) -> tuple[
    RollbackApplicability,
    RollbackReadinessStatus,
    RollbackRiskLevel,
    list[RollbackPrerequisite],
    list[str],
    list[str],
    list[RollbackStep],
    list[str],
    list[str],
    list[str],
]:
    """Deterministically evaluates rollback applicability, prerequisites, and advisory steps.

    Returns:
        (applicability, readiness_status, risk_level, prerequisites, evidence, missing_info, proposed_steps, validation_criteria, limitations, observations)
    """
    prerequisites: list[RollbackPrerequisite] = []
    evidence: list[str] = []
    missing_info: list[str] = []
    proposed_steps: list[RollbackStep] = []
    validation_criteria: list[str] = []
    limitations: list[str] = []
    observations: list[str] = []

    # Record structural evidence
    evidence.append(
        f"Execution '{execution.id}' loaded with mode '{execution.mode}' and status '{execution.status}'."
    )
    evidence.append(
        f"Incident '{incident.id}' confirmed associated (severity: {incident.severity}, status: {incident.status})."
    )
    evidence.append(
        f"Approval '{approval.id}' plan hash verified ({execution.approved_plan_hash[:12]}...)."
    )

    if verification:
        evidence.append(
            f"Post-execution verification record '{verification.id}' found with outcome '{verification.outcome}'."
        )
    else:
        missing_info.append(
            "No post-execution verification record is registered for this execution."
        )

    # Prerequisite 1: Approved Plan Integrity
    prerequisites.append(
        RollbackPrerequisite(
            name="Plan Integrity Verification",
            description="Stored execution approved-plan hash matches referenced human approval.",
            satisfied=True,
            details=f"Plan hash matches approval version {approval.version}.",
        )
    )

    # Prerequisite 2: Recorded Infrastructure Mutation
    has_mutation = execution.mode not in (
        ExecutionMode.SIMULATION.value,
        ExecutionMode.LIVE_DIAGNOSTIC.value,
    )
    prerequisites.append(
        RollbackPrerequisite(
            name="Infrastructure Mutation Recorded",
            description="Operation modified infrastructure and recorded a reversible change state.",
            satisfied=has_mutation,
            details=(
                "Reversible change recorded."
                if has_mutation
                else "No infrastructure modification occurred (read-only diagnostic / simulation)."
            ),
        )
    )

    # Prerequisite 3: Pre-Change Baseline State Captured
    has_prior_state = False
    prerequisites.append(
        RollbackPrerequisite(
            name="Prior State Snapshot Available",
            description="Verified immutable capture of configuration or system state preceding execution.",
            satisfied=has_prior_state,
            details="No configuration state modification was performed; prior state snapshot is not required.",
        )
    )

    # Prerequisite 4: Operator Authorization
    prerequisites.append(
        RollbackPrerequisite(
            name="Human Rollback Authorization",
            description="Explicit human operator authorization granting approval for reversal.",
            satisfied=False,
            details="Pending operator review; human authorization is mandatory prior to any reversal.",
        )
    )

    # Evaluate read-only modes
    if execution.mode in (
        ExecutionMode.SIMULATION.value,
        ExecutionMode.LIVE_DIAGNOSTIC.value,
    ):
        applicability = RollbackApplicability.NOT_APPLICABLE
        readiness_status = RollbackReadinessStatus.NOT_APPLICABLE
        risk_level = RollbackRiskLevel.LOW

        limitations.append(
            f"Rollback applicability: Not Applicable. Execution mode '{execution.mode}' performed "
            "zero infrastructure modifications, service restarts, or configuration updates."
        )
        observations.append(
            "Assessment determined that rollback is NOT APPLICABLE because no infrastructure-changing "
            "remediation was executed."
        )
        validation_criteria.append(
            "Confirm monitoring telemetry remains observable and service health metrics report continuously."
        )
        return (
            applicability,
            readiness_status,
            risk_level,
            prerequisites,
            evidence,
            missing_info,
            proposed_steps,
            validation_criteria,
            limitations,
            observations,
        )

    # For any future hypothetical mutating execution
    applicability = RollbackApplicability.UNSUPPORTED
    readiness_status = RollbackReadinessStatus.BLOCKED
    risk_level = RollbackRiskLevel.HIGH
    limitations.append(
        f"Execution mode '{execution.mode}' is not currently allowlisted for automated rollback."
    )
    return (
        applicability,
        readiness_status,
        risk_level,
        prerequisites,
        evidence,
        missing_info,
        proposed_steps,
        validation_criteria,
        limitations,
        observations,
    )
