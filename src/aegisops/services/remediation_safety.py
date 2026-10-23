from pydantic import ValidationError

from aegisops.workflows.remediation import RemediationPlan
from aegisops.workflows.state import IncidentState

BANNED_COMMAND_PATTERNS = [
    "rm -rf",
    "kubectl delete",
    "kubectl apply",
    "drop table",
    "drop database",
    "truncate table",
    "format c:",
    "mkfs",
    "dd if=",
    "kill -9",
    ":(){ :|:& };:",
    "chmod 777",
    "sudo ",
    "curl | sh",
    "wget | sh",
]

BANNED_RESOLUTION_CLAIMS = [
    "remediation completed",
    "incident is resolved",
    "incident resolved",
    "incident is closed",
    "incident closed",
    "already resolved",
    "successfully remediated",
    "status changed to",
    "mark incident as resolved",
    "mark as resolved",
    "resolve incident",
    "close incident",
    "incident status updated",
]

BANNED_ADVERSARIAL_INJECTIONS = [
    "ignore previous instructions",
    "override previous instructions",
    "disregard all previous instructions",
    "bypass safety",
    "disable safety",
    "skip validation",
    "disable validator",
    "approved by admin",
    "pre-approved",
    "auto-approved",
    "approval not required",
    "skip approval",
    "bypass approval",
    "authorized by administrator",
    "role: admin",
    "acting as admin",
    "i am root",
    "override plan hash",
    "bypass plan hash",
    "suppress audit",
    "disable audit",
    "skip audit",
    "delete audit",
    "cat .env",
    "printenv",
    "gemini_api_key",
    "human_auth_tokens",
    "database_url",
    "/bin/sh",
    "/bin/bash",
    "cmd.exe",
    "powershell.exe",
    "fake metric",
    "invented metric",
]


class RemediationSafetyError(Exception):
    """Raised when a remediation plan fails deterministic safety validation."""


def validate_remediation_safety(
    plan: RemediationPlan | dict,
    rca: dict | None = None,
) -> RemediationPlan:
    if isinstance(plan, dict):
        plan = RemediationPlan.model_validate(plan)

    if not plan.requires_human_approval:
        raise RemediationSafetyError(
            "Remediation plan violates safety invariant: human approval is mandatory."
        )

    if plan.execution_enabled:
        raise RemediationSafetyError(
            "Remediation plan violates safety invariant: execution must be disabled."
        )

    if not plan.recommended_actions:
        raise RemediationSafetyError(
            "Remediation plan must contain at least one recommended action."
        )

    # Check plan-level text for resolution claims and adversarial prompt injections
    plan_text = f"{plan.incident_summary} {plan.planning_basis}".lower()
    for claim in BANNED_RESOLUTION_CLAIMS:
        if claim in plan_text:
            raise RemediationSafetyError(
                f"Remediation plan summary improperly claims incident resolution or status modification: '{claim}'."
            )

    for injection in BANNED_ADVERSARIAL_INJECTIONS:
        if injection in plan_text:
            raise RemediationSafetyError(
                f"Remediation plan contains forbidden adversarial prompt-injection pattern: '{injection}'."
            )

    rca_confidence = (rca or {}).get("overall_confidence", "low")

    for idx, action in enumerate(plan.recommended_actions, start=1):
        if not action.requires_human_approval:
            raise RemediationSafetyError(
                f"Action {idx} ('{action.title}') must require human approval."
            )

        # Check for missing RCA evidence authorizing operational changes
        if action.action_type == "operational_change" and (
            not rca or rca_confidence == "low"
        ):
            raise RemediationSafetyError(
                f"Action {idx} ('{action.title}') proposes an operational change, "
                "but root cause analysis evidence is insufficient or low-confidence. "
                "Only observation or diagnostic actions are permitted."
            )

        # Check text fields for banned executable commands, claims, or injections
        text_corpus = " ".join(
            [
                action.title,
                action.description,
                action.rationale,
                " ".join(action.validation_steps),
                " ".join(action.rollback_considerations),
            ]
        ).lower()

        for pattern in BANNED_COMMAND_PATTERNS:
            if pattern in text_corpus:
                raise RemediationSafetyError(
                    f"Action {idx} contains forbidden executable or destructive pattern: '{pattern}'."
                )

        for claim in BANNED_RESOLUTION_CLAIMS:
            if claim in text_corpus:
                raise RemediationSafetyError(
                    f"Action {idx} improperly claims incident resolution or execution completion: '{claim}'."
                )

        for injection in BANNED_ADVERSARIAL_INJECTIONS:
            if injection in text_corpus:
                raise RemediationSafetyError(
                    f"Action {idx} contains forbidden adversarial prompt-injection pattern: '{injection}'."
                )

    return plan


def validate_remediation_safety_node(state: IncidentState) -> dict:
    plan_data = state.get("remediation_plan")
    if not plan_data or state.get("remediation_error"):
        return {}

    try:
        validated_plan = validate_remediation_safety(
            plan_data,
            rca=state.get("rca"),
        )
        return {
            "remediation_plan": validated_plan.model_dump(),
            "remediation_error": None,
        }
    except (
        RemediationSafetyError,
        ValidationError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as exc:
        return {
            "remediation_plan": None,
            "remediation_error": f"Safety validation failed: {exc}",
        }
