import hashlib
import json
from typing import Any

from pydantic import ValidationError

from aegisops.workflows.remediation import RemediationPlan


class PlanIntegrityError(Exception):
    """Raised when plan integrity check fails or snapshot has been tampered with."""


def canonicalize_plan(plan: RemediationPlan | dict[str, Any]) -> str:
    """Serializes a RemediationPlan or dict into canonical JSON with sorted keys and compact separators."""
    if isinstance(plan, RemediationPlan):
        data = plan.model_dump(mode="json")
    elif isinstance(plan, dict):
        data = plan
    else:
        raise TypeError(f"Expected RemediationPlan or dict, got {type(plan).__name__}")

    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_plan_hash(plan: RemediationPlan | dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hex digest for a remediation plan."""
    canonical = canonicalize_plan(plan)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_plan_integrity(
    snapshot: dict[str, Any],
    expected_hash: str,
) -> bool:
    """Verifies that the stored snapshot matches the expected hash and enforces safety invariants."""
    try:
        # Re-validate with Pydantic model to verify domain structure & invariants
        validated = RemediationPlan.model_validate(snapshot)
        if validated.execution_enabled:
            return False
        if not validated.requires_human_approval:
            return False

        computed = compute_plan_hash(snapshot)
        return (
            hashlib.sha256(computed.encode("utf-8")).digest()
            == hashlib.sha256(expected_hash.encode("utf-8")).digest()
        )
    except (ValidationError, ValueError, TypeError, KeyError, AttributeError):
        return False
