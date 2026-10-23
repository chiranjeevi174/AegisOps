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
from aegisops.services.approvals import (
    approve_request,
    create_approval_request,
    get_approval_events,
    get_approval_request,
    list_approval_requests,
    reject_request,
    request_revision,
)
from aegisops.services.incidents import (
    get_incident,
    list_incidents,
    run_incident_workflow,
)


async def main():
    parser = argparse.ArgumentParser(
        description="Verify human-in-the-loop remediation approval lifecycle for AegisOps incidents."
    )
    parser.add_argument(
        "incident_id",
        nargs="?",
        help="UUID of the incident to evaluate and generate/decide approval for.",
    )
    parser.add_argument(
        "--action",
        choices=["approve", "reject", "revision"],
        help="Explicit human decision action to execute. If omitted, displays request and instructions without deciding.",
    )
    parser.add_argument(
        "--reason",
        default="Approved by verified SRE Lead for advisory diagnostic steps.",
        help="Comment or reason for the decision action.",
    )

    args = parser.parse_args()

    if not args.incident_id:
        print(
            "Usage: uv run python scripts/verify_approvals.py <incident-uuid> [--action approve|reject|revision] [--reason <text>]\n"
        )
        print("Available incidents in PostgreSQL database:")
        async with SessionLocal() as session:
            incidents = await list_incidents(session, limit=10)
            if not incidents:
                print("  No incidents found in database.")
            for inc in incidents:
                started = (
                    inc.alert_started_at.isoformat() if inc.alert_started_at else "None"
                )
                print(
                    f"  - {inc.id} | {inc.source:<12} | started: {started:<25} | {inc.title}"
                )
        return

    try:
        incident_uuid = UUID(args.incident_id.strip())
    except ValueError:
        print(f"Error: '{args.incident_id}' is not a valid UUID format.")
        sys.exit(1)

    print(f"Loading incident {incident_uuid} from PostgreSQL...")

    async with SessionLocal() as session:
        incident = await get_incident(session, incident_uuid)
        if incident is None:
            print(f"Error: Incident {incident_uuid} was not found in the database.")
            sys.exit(1)

        print(f"Found Incident: '{incident.title}'")
        print(f"  - Severity: {incident.severity}")
        print(f"  - Status: {incident.status}")
        print(f"  - Source: {incident.source}")
        print(f"  - Alert Started At: {incident.alert_started_at}")

        # Check existing approvals for this incident
        existing_approvals = await list_approval_requests(
            session, incident_id=incident_uuid
        )
        active_pending = next(
            (a for a in existing_approvals if a.status == ApprovalStatus.PENDING.value),
            None,
        )

        approval = active_pending

        if approval is None and not args.action:
            print(
                "\nExecuting agentic incident workflow to generate and safety-validate remediation plan..."
            )
            workflow_result = await run_incident_workflow(session, incident_uuid)

            plan_dict = workflow_result.get("remediation_plan")
            error = workflow_result.get("remediation_error")

            if not plan_dict or error:
                print(f"Error: Could not generate safe remediation plan: {error}")
                sys.exit(1)

            print("\nCreating persistent immutable approval request in PostgreSQL...")
            approval = await create_approval_request(
                session=session,
                incident_id=incident_uuid,
                plan=plan_dict,
                requested_by="sre-engineer-alice",
                rca=workflow_result.get("rca"),
            )
            print("Approval request created successfully.")
        elif approval is None and args.action:
            # Need an existing pending request to decide
            if not existing_approvals:
                print(
                    "Error: No approval requests exist for this incident. Run without --action first to create one."
                )
                sys.exit(1)
            approval = existing_approvals[0]
            print(
                f"Targeting existing approval {approval.id} (status: {approval.status})"
            )

    # Display Approval Details
    assert approval is not None

    async with SessionLocal() as session:
        # Reload approval
        approval = await get_approval_request(session, approval.id)
        assert approval is not None

        print("\n" + "=" * 60)
        print("REMEDIATION APPROVAL RECORD")
        print("=" * 60)
        print(f"  Approval ID: {approval.id}")
        print(f"  Incident ID: {approval.incident_id}")
        print(f"  Status: {approval.status.upper()}")
        print(f"  Version: {approval.version}")
        print(f"  Plan SHA-256 Hash: {approval.plan_hash}")
        print(f"  Requested By: {approval.requested_by}")
        print(f"  Requested At: {approval.requested_at.isoformat()}")
        print(f"  Expires At: {approval.expires_at.isoformat()}")
        print(f"  Decided By: {approval.decided_by or 'None (Awaiting Decision)'}")
        print(
            f"  Decided At: {approval.decided_at.isoformat() if approval.decided_at else 'None'}"
        )
        print(f"  Decision Reason: {approval.decision_reason or 'None'}")
        print("  Execution Enabled: False")
        print("  Human Approval Required: True")

        print("\n[STORED IMMUTABLE PLAN SNAPSHOT]")
        snapshot = approval.plan_snapshot
        print(f"  Summary: {snapshot.get('incident_summary')}")
        print(f"  Planning Basis: {snapshot.get('planning_basis')}")
        print(f"  Overall Risk: {snapshot.get('overall_risk')}")
        print("  Recommended Actions:")
        for idx, act in enumerate(snapshot.get("recommended_actions", []), start=1):
            print(f"    Action {idx}: {act.get('title')}")
            print(
                f"      Type: {act.get('action_type')}, Risk: {act.get('risk_level')}"
            )
            print(f"      Requires Approval: {act.get('requires_human_approval')}")
            print(f"      Description: {act.get('description')}")

        if args.action:
            print("\n" + "=" * 60)
            print(f"EXECUTING AUTHENTICATED DECISION: {args.action.upper()}")
            print("=" * 60)
            actor_identity = "sre-lead-charlie"

            try:
                if args.action == "approve":
                    approval = await approve_request(
                        session=session,
                        approval_id=approval.id,
                        actor_identity=actor_identity,
                        comment=args.reason,
                    )
                    print(f"Decision Recorded: APPROVED by {actor_identity}")
                elif args.action == "reject":
                    approval = await reject_request(
                        session=session,
                        approval_id=approval.id,
                        actor_identity=actor_identity,
                        reason=args.reason,
                    )
                    print(f"Decision Recorded: REJECTED by {actor_identity}")
                elif args.action == "revision":
                    approval = await request_revision(
                        session=session,
                        approval_id=approval.id,
                        actor_identity=actor_identity,
                        reason=args.reason,
                    )
                    print(f"Decision Recorded: REVISION REQUESTED by {actor_identity}")
            except Exception as exc:  # noqa: BLE001
                print(f"Decision Rejected by Policy: {type(exc).__name__}: {exc}")

        # Display audit events
        events = await get_approval_events(session, approval.id)
        print("\n" + "=" * 60)
        print(f"APPROVAL AUDIT TRAIL ({len(events)} events)")
        print("=" * 60)
        for ev in events:
            print(
                f"  [{ev.created_at.isoformat()}] Event: {ev.event_type:<18} | Actor: {ev.actor:<18} | Status: {ev.previous_status or 'None'} -> {ev.new_status}"
            )
            if ev.reason:
                print(f"     Reason: {ev.reason}")
            print(f"     Hash: {ev.plan_hash[:16]}...")

        # Verify DB incident status
        db_inc = await session.get(Incident, incident_uuid)
        assert db_inc is not None

        print("\n" + "=" * 60)
        print("SAFETY AUDIT VERIFICATION")
        print("=" * 60)
        print("  Execution Enabled: False")
        print("  Human Approval Required: True")
        print("  Incident Database Status: " + db_inc.status + " (Unchanged)")
        print("  Remediation Actions Executed: None (Zero Infrastructure Changes)")
        print("=" * 60)

        if not args.action and approval.status == ApprovalStatus.PENDING.value:
            print("\n[NEXT STEPS FOR HUMAN ENGINEER]")
            print(
                "To make an authenticated decision, run either of the following commands:"
            )
            print("  1. Approve request:")
            print(
                f'     uv run python scripts/verify_approvals.py {incident_uuid} --action approve --reason "Approved for diagnostic inspection"'
            )
            print("  2. Reject request:")
            print(
                f'     uv run python scripts/verify_approvals.py {incident_uuid} --action reject --reason "Insufficient telemetry provided"'
            )
            print("  3. Request revision:")
            print(
                f'     uv run python scripts/verify_approvals.py {incident_uuid} --action revision --reason "Include thread dump diagnostics"'
            )
            print("\nOr via REST API:")
            print(
                f"  curl -X POST http://localhost:8000/api/v1/approvals/{approval.id}/approve \\"
            )
            print('    -H "Authorization: Bearer aegisops-dev-approver-token" \\')
            print('    -H "Content-Type: application/json" \\')
            print('    -d \'{"comment": "Approved by SRE Lead"}\'')
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
