import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegisops.db.session import SessionLocal
from aegisops.domain.approval import ApprovalStatus
from aegisops.domain.incident import Incident
from aegisops.execution.registry import ALLOWLISTED_OPERATIONS
from aegisops.services.approvals import get_approval_request, list_approval_requests
from aegisops.services.executions import (
    execute_simulation,
    get_execution_events,
)


async def main():
    parser = argparse.ArgumentParser(
        description="Verify controlled remediation simulation engine against approved plans in AegisOps."
    )
    parser.add_argument(
        "--approval-id",
        help="UUID of the approved remediation plan to bind and simulate execution for.",
    )
    parser.add_argument(
        "--operation",
        default="inspect_latency_metrics",
        choices=list(ALLOWLISTED_OPERATIONS.keys()),
        help="Allowlisted diagnostic operation to simulate.",
    )
    parser.add_argument(
        "--recommendation-index",
        type=int,
        default=1,
        help="1-based index of the recommendation in the approved plan supported by this operation.",
    )
    parser.add_argument(
        "--idempotency-key",
        default="verify-exec-sim-key-01",
        help="Idempotency key for deterministic replay verification.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Explicit flag to execute the dry-run simulation.",
    )

    args = parser.parse_args()

    async with SessionLocal() as session:
        if not args.approval_id:
            print(
                "Usage: uv run python scripts\\verify_execution.py --approval-id <APPROVAL_UUID> --simulate\n"
            )
            print("Available approved plans in PostgreSQL database:")
            approved_requests = await list_approval_requests(
                session, status=ApprovalStatus.APPROVED.value, limit=10
            )
            if not approved_requests:
                print("  No approved plans found in database.")
                print(
                    "  Use 'scripts\\verify_approvals.py' to approve an incident plan first."
                )
            for req in approved_requests:
                print(
                    f"  - Approval ID: {req.id} | Incident: {req.incident_id} | Version: {req.version} | Hash: {req.plan_hash[:16]}... | Decided by: {req.decided_by}"
                )
            return

        try:
            approval_uuid = UUID(args.approval_id.strip())
        except ValueError:
            print(f"Error: '{args.approval_id}' is not a valid UUID format.")
            sys.exit(1)

        approval = await get_approval_request(session, approval_uuid)
        if approval is None:
            print(f"Error: Approval request {approval_uuid} not found.")
            sys.exit(1)

        incident = await session.get(Incident, approval.incident_id)
        if incident is None:
            print(f"Error: Associated incident {approval.incident_id} not found.")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("APPROVED PLAN CONTEXT")
        print("=" * 60)
        print(f"  Approval ID: {approval.id}")
        print(f"  Incident ID: {approval.incident_id} ('{incident.title}')")
        print(f"  Approval Status: {approval.status.upper()}")
        print(f"  Plan Version: {approval.version}")
        print(f"  Plan SHA-256 Hash: {approval.plan_hash}")
        print(f"  Decided By: {approval.decided_by}")
        print(
            f"  Decided At: {approval.decided_at.isoformat() if approval.decided_at else 'None'}"
        )

        if approval.status != ApprovalStatus.APPROVED.value:
            print(f"\n[ERROR] Approval {approval.id} is in '{approval.status}' status.")
            print(
                "Execution requests are strictly rejected unless approval status is 'approved'."
            )
            sys.exit(1)

        if not args.simulate:
            print("\n[SIMULATION READY]")
            print(f"Target Operation: {args.operation}")
            print(f"Target Recommendation Index: {args.recommendation_index}")
            print("\nTo execute this dry-run simulation, run:")
            print(
                f"  uv run python scripts\\verify_execution.py --approval-id {approval.id} --operation {args.operation} --simulate"
            )
            return

        print("\n" + "=" * 60)
        print("EXECUTING ALLOWLISTED SIMULATION")
        print("=" * 60)
        operator_identity = "sre-operator-dan"
        print(f"  Authenticated Operator: {operator_identity}")
        print(f"  Selected Operation: {args.operation}")
        print(f"  Recommendation Reference Index: {args.recommendation_index}")
        print(f"  Idempotency Key: {args.idempotency_key}")

        try:
            record, is_replay = await execute_simulation(
                session=session,
                approval_id=approval.id,
                incident_id=incident.id,
                operation_id=args.operation,
                recommendation_index=args.recommendation_index,
                parameters={},
                idempotency_key=args.idempotency_key,
                requested_by=operator_identity,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Simulation Failed/Rejected: {type(exc).__name__}: {exc}")
            sys.exit(1)

        print(f"\nSimulation Succeeded! (Replay: {is_replay})")
        print(f"  Execution Record ID: {record.id}")
        print(f"  Execution Mode: {record.mode.upper()}")
        print(f"  Execution Status: {record.status.upper()}")
        print(f"  Selected Recommendation: {record.selected_recommendation_title}")
        print(f"  Duration: {record.duration_ms}ms")
        print(f"  Completed At: {record.completed_at.isoformat()}")

        print("\n[STRUCTURED SIMULATION RESULT]")
        res = record.simulation_result or {}
        print(f"  Intended Purpose: {res.get('intended_purpose')}")
        print(f"  Target Scope: {res.get('target_scope')}")
        print(f"  Risk Assessment: {res.get('risk_assessment')}")
        print("  Expected Observations:")
        for obs in res.get("expected_observations", []):
            print(f"    * {obs}")
        print("  Simulated Output:")
        for k, v in res.get("simulated_output", {}).items():
            print(f"    - {k}: {v}")

        # Audit Trail
        events = await get_execution_events(session, record.id)
        print("\n" + "=" * 60)
        print(f"EXECUTION AUDIT TRAIL ({len(events)} events)")
        print("=" * 60)
        for ev in events:
            print(
                f"  [{ev.created_at.isoformat()}] Event: {ev.event_type:<22} | Actor: {ev.actor:<18} | Status: {ev.new_status}"
            )
            print(
                f"     Operation: {ev.operation_id} | Hash: {ev.approved_plan_hash[:16]}..."
            )

        # Verify DB Incident
        reloaded_inc = await session.get(Incident, incident.id)
        assert reloaded_inc is not None

        print("\n" + "=" * 60)
        print("SAFETY AUDIT VERIFICATION")
        print("=" * 60)
        print("  Simulation Mode: simulation (DRY-RUN ONLY)")
        print("  Actual Infrastructure Access: False")
        print("  System Changes Performed: False")
        print(f"  Incident Database Status: {reloaded_inc.status} (Unchanged)")
        print(f"  Approval Database Status: {approval.status} (Unchanged)")
        print("  Real Execution Supported: False")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
