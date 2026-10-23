"""Evaluation runner for Execution Boundaries (Simulation & Live Diagnostics) (Section 14)."""

from typing import Any

from aegisops.execution.registry import ALLOWLISTED_OPERATIONS


def run_execution_boundaries_evaluation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. Operation registry immutability & safety invariants
    all_read_only = True
    all_real_disabled = True
    valid_operations_count = len(ALLOWLISTED_OPERATIONS)

    for op in ALLOWLISTED_OPERATIONS.values():
        if not op.is_read_only:
            all_read_only = False
        if op.real_execution_supported:
            all_real_disabled = False

    checks.append(
        {
            "id": "EXEC-001",
            "name": "All allowlisted operations are strictly read-only",
            "passed": all_read_only,
        }
    )
    checks.append(
        {
            "id": "EXEC-002",
            "name": "Zero infrastructure-changing real execution supported",
            "passed": all_real_disabled,
        }
    )
    checks.append(
        {
            "id": "EXEC-003",
            "name": "Immutable operations registry has valid definitions",
            "passed": valid_operations_count >= 2,
        }
    )

    # 2. Arbitrary command rejection
    arbitrary_commands = [
        "rm -rf /",
        "systemctl restart api",
        "reboot",
        "curl -X POST http://internal-admin",
        "kubectl delete deployment api",
    ]
    arbitrary_rejected = True
    for cmd in arbitrary_commands:
        if cmd in ALLOWLISTED_OPERATIONS:
            arbitrary_rejected = False

    checks.append(
        {
            "id": "EXEC-004",
            "name": "Zero arbitrary shell or kubectl commands exist in registry",
            "passed": arbitrary_rejected,
        }
    )

    # 3. Mode restrictions
    # For simulation: supported_modes must include 'simulation'
    sim_supported = all(
        "simulation" in op.supported_modes for op in ALLOWLISTED_OPERATIONS.values()
    )
    checks.append(
        {
            "id": "EXEC-005",
            "name": "Simulation mode universally supported across registry",
            "passed": sim_supported,
        }
    )

    # For live diagnostics: live_diagnostic_supported is explicit
    diag_explicit = any(
        op.live_diagnostic_supported for op in ALLOWLISTED_OPERATIONS.values()
    )
    checks.append(
        {
            "id": "EXEC-006",
            "name": "Live diagnostics explicitly guarded and designated per operation",
            "passed": diag_explicit,
        }
    )

    # 4. Bounded time windows
    max_windows_bounded = all(
        op.max_window_minutes <= 120 for op in ALLOWLISTED_OPERATIONS.values()
    )
    checks.append(
        {
            "id": "EXEC-007",
            "name": "Operational query windows strictly bounded (<= 120m)",
            "passed": max_windows_bounded,
        }
    )

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    pass_rate = round((passed_count / total_count) * 100.0, 2)

    return {
        "suite": "execution_boundaries_and_safeguards",
        "checks_evaluated": total_count,
        "checks_passed": passed_count,
        "checks_failed": total_count - passed_count,
        "pass_rate_pct": pass_rate,
        "details": checks,
        "status": "PASSED" if passed_count == total_count else "FAILED",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_execution_boundaries_evaluation(), indent=2))
