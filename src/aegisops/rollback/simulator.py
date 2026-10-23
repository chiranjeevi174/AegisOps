from datetime import UTC, datetime

from aegisops.domain.execution import ExecutionMode, RemediationExecution
from aegisops.domain.rollback import RollbackApplicability, RollbackRiskLevel
from aegisops.rollback.schemas import (
    RollbackPrerequisite,
    RollbackSimulationResult,
)


def simulate_rollback(
    execution: RemediationExecution,
    applicability: RollbackApplicability,
    risk_level: RollbackRiskLevel,
    prerequisites: list[RollbackPrerequisite],
) -> RollbackSimulationResult:
    """Deterministically models a hypothetical rollback without executing system commands.

    Strictly simulation-only: zero subprocess calls, zero infrastructure mutation,
    zero arbitrary script execution.
    """
    now = datetime.now(UTC)
    simulated_actions: list[str] = []
    notes: list[str] = []

    if execution.mode in (
        ExecutionMode.SIMULATION.value,
        ExecutionMode.LIVE_DIAGNOSTIC.value,
    ):
        simulated_actions.append(
            f"Evaluated read-only operation '{execution.operation_id}'. Confirmed zero state changes."
        )
        simulated_actions.append(
            "Determined that no infrastructure rollback actions are necessary or applicable."
        )
        notes.append(
            "Truthful assessment: The original execution was read-only; no infrastructure modifications occurred."
        )
        notes.append(
            "Simulation confirmed that system state remains unmodified and operational."
        )
        return RollbackSimulationResult(
            simulation_mode="simulation_only",
            simulated_at=now,
            can_safely_simulate=True,
            simulated_actions=simulated_actions,
            simulated_target_state="Original unmodified production baseline state (identical to current state)",
            risk_assessment_summary="Risk is minimal (LOW) because no infrastructure modification occurred.",
            notes=notes,
        )

    # Future hypothetical mutating execution
    simulated_actions.append(
        f"Analyzed mutating operation '{execution.operation_id}'. Reversal requires operator-specified snapshot."
    )
    notes.append(
        "Simulation-only: Actual execution of rollback commands is strictly disabled."
    )
    notes.append("Explicit human authorization is required before any rollback action.")
    return RollbackSimulationResult(
        simulation_mode="simulation_only",
        simulated_at=now,
        can_safely_simulate=False,
        simulated_actions=simulated_actions,
        simulated_target_state="Hypothetical pre-execution state (requires explicit operator review)",
        risk_assessment_summary=f"Risk is {risk_level.value.upper()} due to pending prerequisite verification.",
        notes=notes,
    )
