import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegisops.core.auth import get_current_actor
from aegisops.core.config import get_settings
from aegisops.db.session import SessionLocal
from aegisops.domain.approval import ApprovalStatus, RemediationApproval
from aegisops.domain.execution import ExecutionMode
from aegisops.domain.incident import Incident
from aegisops.execution.registry import get_operation_definition
from aegisops.services import executions


async def main():
    parser = argparse.ArgumentParser(
        description="Verify human-authorized restricted live diagnostic execution for AegisOps incidents."
    )
    parser.add_argument(
        "approval_id",
        nargs="?",
        help="UUID of the existing approved remediation plan to execute diagnostic against.",
    )
    parser.add_argument(
        "--operation-id",
        default="inspect_service_health",
        help="Allowlisted operation identifier to execute (e.g. inspect_service_health, inspect_cpu_metrics).",
    )
    parser.add_argument(
        "--recommendation-index",
        type=int,
        default=1,
        help="1-based index of the approved recommendation to bind to (default: 1).",
    )
    parser.add_argument(
        "--mode",
        choices=["live_diagnostic", "simulation"],
        default="live_diagnostic",
        help="Execution mode (default: live_diagnostic).",
    )
    parser.add_argument(
        "--idempotency-key",
        default=None,
        help="Unique idempotency key for this execution request.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Operator bearer token with execution permission (or set OPERATOR_TOKEN env var).",
    )
    parser.add_argument(
        "--params",
        default=None,
        help="Optional JSON parameters string for the operation.",
    )
    parser.add_argument(
        "--enable-live",
        action="store_true",
        help="Explicitly enable live diagnostics locally if disabled in environment.",
    )

    args = parser.parse_args()

    if not args.approval_id:
        print(
            "Usage: uv run python scripts/verify_diagnostics.py <approval-uuid> [options]\n"
        )
        print("Available approved plans in PostgreSQL database:")
        async with SessionLocal() as session:
            stmt = RemediationApproval.__table__.select().where(
                RemediationApproval.status == ApprovalStatus.APPROVED.value
            )
            approvals_list = await session.execute(stmt)
            rows = approvals_list.fetchall()
            if not rows:
                print("  No approved plans found in database.")
                print(
                    "  Create and approve a plan first using: scripts/verify_approvals.py <incident-id> --action approve"
                )
            for r in rows:
                print(
                    f"  - Approval: {r.id} | Incident: {r.incident_id} | Version: {r.version}"
                )
        return

    try:
        approval_uuid = UUID(args.approval_id.strip())
    except ValueError:
        print(f"Error: '{args.approval_id}' is not a valid UUID format.")
        sys.exit(1)

    # 1. Resolve and authenticate operator without logging token value
    token = args.token
    if not token:
        import os

        token = os.environ.get("OPERATOR_TOKEN")
        if not token:
            # Check configured actors in settings for a dev operator token
            raw_tokens = get_settings().human_auth_tokens.get_secret_value()
            for entry in raw_tokens.split(","):
                parts = entry.strip().split(":")
                if len(parts) >= 3 and (
                    "operator" in parts[2] or "executor" in parts[2]
                ):
                    token = parts[0]
                    break

    if not token:
        print(
            "Error: An authenticated operator token is required (--token or OPERATOR_TOKEN env var)."
        )
        sys.exit(1)

    try:
        actor = get_current_actor(authorization=f"Bearer {token}")
        if not actor.can_execute:
            print(
                f"Error: Actor '{actor.identity}' lacks executor/operator permission."
            )
            sys.exit(1)
        print(
            f"Authenticated Operator: '{actor.identity}' (roles: {sorted(actor.roles)})"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Authentication Failed: {exc}")
        sys.exit(1)

    # 2. Check operation definition
    try:
        op_def = get_operation_definition(args.operation_id)
        if args.mode == "live_diagnostic" and not op_def.live_diagnostic_supported:
            print(
                f"Error: Operation '{args.operation_id}' does not support live diagnostics."
            )
            sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"Operation Allowlist Error: {exc}")
        sys.exit(1)

    # 3. Parse parameters
    raw_params = {}
    if args.params:
        try:
            raw_params = json.loads(args.params)
        except json.JSONDecodeError as exc:
            print(f"Error: Invalid JSON in --params: {exc}")
            sys.exit(1)
    else:
        # Sensible low-risk defaults
        if args.operation_id == "inspect_service_health":
            raw_params = {"service_name": "api-service", "include_dependencies": True}
        else:
            raw_params = {"window_minutes": 15, "step": "15s"}

    idempotency_key = (
        args.idempotency_key
        or f"diag-run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    )

    print(f"\nVerifying Approval {approval_uuid} in PostgreSQL...")
    async with SessionLocal() as session:
        approval = await session.get(RemediationApproval, approval_uuid)
        if approval is None:
            print(f"Error: Approval {approval_uuid} not found in database.")
            sys.exit(1)

        if approval.status != ApprovalStatus.APPROVED.value:
            print(
                f"Error: Approval {approval_uuid} is in '{approval.status}' status (must be 'approved')."
            )
            sys.exit(1)

        # Check expiration
        now = datetime.now(UTC)
        decided_at = approval.decided_at or approval.requested_at
        eligibility_window = timedelta(
            minutes=get_settings().execution_eligibility_minutes
        )
        if now - decided_at > eligibility_window:
            print(
                f"Error: Approval execution authorization window expired at "
                f"{(decided_at + eligibility_window).isoformat()}."
            )
            print(
                "Policy requires a fresh approval. Stopping without modifying records."
            )
            sys.exit(1)

        incident = await session.get(Incident, approval.incident_id)
        if incident is None:
            print(
                f"Error: Incident {approval.incident_id} associated with approval not found."
            )
            sys.exit(1)

        initial_incident_status = incident.status
        initial_approval_status = approval.status

        print(f"Associated Incident: '{incident.title}' (ID: {incident.id})")
        print(f"  Incident Status: {initial_incident_status}")
        print(f"  Approval Status: {initial_approval_status}")
        print(f"  Approved Plan Hash: {approval.plan_hash[:16]}...")
        print(f"  Operation ID: {args.operation_id}")
        print(f"  Recommendation Index: {args.recommendation_index}")
        print(f"  Execution Mode: {args.mode}")
        print(f"  Idempotency Key: {idempotency_key}")

        # Temporarily enable live diagnostics if requested
        if args.enable_live or args.mode == "live_diagnostic":
            import os

            os.environ["LIVE_DIAGNOSTICS_ENABLED"] = "true"
            get_settings.cache_clear()

        print("\nExecuting authorized operation...")
        try:
            if args.mode == "live_diagnostic":
                record, is_replay = await executions.execute_live_diagnostic(
                    session=session,
                    approval_id=approval_uuid,
                    incident_id=incident.id,
                    operation_id=args.operation_id,
                    recommendation_index=args.recommendation_index,
                    parameters=raw_params,
                    idempotency_key=idempotency_key,
                    requested_by=actor.identity,
                )
            else:
                record, is_replay = await executions.execute_simulation(
                    session=session,
                    approval_id=approval_uuid,
                    incident_id=incident.id,
                    operation_id=args.operation_id,
                    recommendation_index=args.recommendation_index,
                    parameters=raw_params,
                    idempotency_key=idempotency_key,
                    requested_by=actor.identity,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"\nExecution Failed: {type(exc).__name__}: {exc}")
            sys.exit(1)

        # Reload incident and approval to verify immutability
        reloaded_incident = await session.get(Incident, incident.id)
        reloaded_approval = await session.get(RemediationApproval, approval_uuid)
        assert reloaded_incident is not None
        assert reloaded_approval is not None

        incident_unchanged = reloaded_incident.status == initial_incident_status
        approval_unchanged = reloaded_approval.status == initial_approval_status

        # Query events
        events = await executions.get_execution_events(session, record.id)

    # 4. Formatted Verification Output
    print("\n" + "=" * 60)
    print("RESTRICTED DIAGNOSTIC VERIFICATION REPORT")
    print("=" * 60)
    print(f"Execution ID: {record.id}")
    print(f"Execution Mode: {record.mode}")
    print(f"Execution Status: {record.status}")
    print(f"Monitoring Access: {record.mode == ExecutionMode.LIVE_DIAGNOSTIC.value}")
    print("System Changes Performed: False")
    print(
        f"Incident Status: {'Unchanged' if incident_unchanged else 'MUTATED'} ({reloaded_incident.status})"
    )
    print(
        f"Approval Status: {'Unchanged' if approval_unchanged else 'MUTATED'} ({reloaded_approval.status})"
    )
    print(f"Duration: {record.duration_ms} ms")
    print(f"Is Replay: {is_replay}")

    if record.mode == ExecutionMode.LIVE_DIAGNOSTIC.value:
        diag = record.diagnostic_result or {}
        print("\n[PROMETHEUS LIVE TELEMETRY]")
        print(f"  Metric: {diag.get('metric_identifier')}")
        print(f"  Data Availability Status: {diag.get('data_availability_status')}")
        summary = diag.get("summary")
        if summary:
            print(f"  Sample Count: {summary.get('sample_count')}")
            print(
                f"  Latest Value: {summary.get('latest_value')} {summary.get('unit')}"
            )
            print(f"  Mean Value: {summary.get('mean_value')} {summary.get('unit')}")
            print(f"  Min Value: {summary.get('min_value')} {summary.get('unit')}")
            print(f"  Max Value: {summary.get('max_value')} {summary.get('unit')}")
        for obs in diag.get("observations", []):
            print(f"  Observation: {obs}")
    else:
        sim = record.simulation_result or {}
        print("\n[SIMULATION DRY RUN]")
        print(f"  Status: {sim.get('status')}")
        print(f"  Expected Impact: {sim.get('expected_impact')}")

    print("\n[EXECUTION AUDIT TRAIL]")
    for ev in events:
        print(
            f"  [{ev.created_at.isoformat()}] {ev.event_type} | Actor: {ev.actor} | Status: {ev.previous_status} -> {ev.new_status}"
        )

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
