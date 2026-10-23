from aegisops.domain.execution import ExecutionMode, RemediationExecution
from aegisops.domain.rollback import RollbackApplicability, RollbackRiskLevel
from aegisops.domain.verification import ExecutionVerification, VerificationOutcome
from aegisops.rollback.schemas import RollbackPrerequisite


def assess_rollback_risk(
    execution: RemediationExecution,
    applicability: RollbackApplicability,
    prerequisites: list[RollbackPrerequisite],
    verification: ExecutionVerification | None,
) -> tuple[RollbackRiskLevel, list[str]]:
    """Deterministically evaluates the qualitative operational risk of a hypothetical rollback.

    Returns:
        (risk_level, risk_factors)
    """
    factors: list[str] = []

    # Read-only operations have no mutating impact
    if execution.mode in (
        ExecutionMode.SIMULATION.value,
        ExecutionMode.LIVE_DIAGNOSTIC.value,
    ):
        factors.append(
            "Execution mode is read-only; no infrastructure state was modified, so operational risk is minimal."
        )
        return RollbackRiskLevel.LOW, factors

    # Evaluate verification quality if present
    if verification:
        if verification.outcome == VerificationOutcome.DIAGNOSTIC_VERIFIED.value:
            factors.append(
                "Completed post-execution verification provides baseline telemetry context."
            )
        elif verification.outcome == VerificationOutcome.INCONCLUSIVE.value:
            factors.append(
                "Post-execution verification was inconclusive; absence of verified telemetry increases rollback risk."
            )
        elif verification.outcome == VerificationOutcome.VERIFICATION_FAILED.value:
            factors.append(
                "Post-execution verification failed; telemetry integrity is unconfirmed."
            )
    else:
        factors.append(
            "Missing post-execution verification telemetry increases operational uncertainty."
        )

    # Check prerequisite completeness
    unsatisfied = [p.name for p in prerequisites if not p.satisfied]
    if unsatisfied:
        factors.append(f"Unsatisfied rollback prerequisites: {', '.join(unsatisfied)}.")
        return RollbackRiskLevel.HIGH, factors

    return RollbackRiskLevel.MEDIUM, factors
