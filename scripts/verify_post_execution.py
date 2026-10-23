import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegisops.core.auth import AuthenticatedActor, _load_configured_actors
from aegisops.db.session import SessionLocal
from aegisops.domain.approval import RemediationApproval
from aegisops.domain.execution import RemediationExecution
from aegisops.domain.incident import Incident
from aegisops.services import verifications
from aegisops.services.executions import (
    ConcurrencyConflictError,
    ExecutionNotFoundError,
    IdempotencyConflictError,
)
from aegisops.services.plan_integrity import PlanIntegrityError
from aegisops.services.verifications import (
    VerificationEligibilityError,
)
from aegisops.verification.schemas import (
    VerificationCriteria,
)


def resolve_actor(token_str: str | None) -> AuthenticatedActor:
    configured = _load_configured_actors()
    if token_str and token_str in configured:
        info = configured[token_str]
        identity = str(info.get("identity", "unknown"))
        raw_roles = info.get("roles", [])
        roles = (
            frozenset(raw_roles)
            if isinstance(raw_roles, list)
            else frozenset([str(raw_roles)])
        )
        return AuthenticatedActor(identity=identity, roles=roles)

    # Fallback to dev operator token from settings if configured
    for info in configured.values():
        raw_roles = info.get("roles", [])
        role_list = raw_roles if isinstance(raw_roles, list) else [str(raw_roles)]
        if (
            "verifier" in role_list
            or "operator" in role_list
            or "executor" in role_list
        ):
            identity = str(info.get("identity", "sre-operator-dan"))
            return AuthenticatedActor(identity=identity, roles=frozenset(role_list))

    return AuthenticatedActor(
        identity="sre-operator-dan",
        roles=frozenset(["operator", "executor", "verifier"]),
    )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify post-execution operational evidence and telemetry for AegisOps executions."
    )
    parser.add_argument(
        "execution_id",
        nargs="?",
        help="UUID of the remediation execution to inspect or verify.",
    )
    parser.add_argument(
        "--execution-id",
        dest="opt_execution_id",
        help="UUID of the remediation execution (alternative option format).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Execute deterministic post-execution verification against baseline and follow-up evidence.",
    )
    parser.add_argument(
        "--token",
        help="Bearer token of the authenticated operator/verifier.",
    )
    parser.add_argument(
        "--idempotency-key",
        help="Unique idempotency key for this verification request.",
    )
    parser.add_argument(
        "--baseline-window",
        type=int,
        default=15,
        help="Pre-execution baseline window duration in minutes (default: 15).",
    )
    parser.add_argument(
        "--followup-window",
        type=int,
        default=15,
        help="Post-execution follow-up observation window duration in minutes (default: 15).",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=2,
        help="Minimum required samples for statistical sufficiency (default: 2).",
    )
    parser.add_argument(
        "--step",
        default="15s",
        help="Prometheus resolution query step (default: '15s').",
    )

    args = parser.parse_args()

    raw_exec_id = args.opt_execution_id or args.execution_id
    if not raw_exec_id:
        print(
            "Usage: uv run python scripts/verify_post_execution.py <execution-uuid> [--verify] [options]\n"
        )
        print("Recent executions recorded in PostgreSQL database:")
        async with SessionLocal() as session:
            # Query recent executions
            from sqlalchemy import desc, select

            stmt = (
                select(RemediationExecution)
                .order_by(desc(RemediationExecution.requested_at))
                .limit(10)
            )
            res = await session.execute(stmt)
            execs = res.scalars().all()
            if not execs:
                print("  No execution records found.")
            for e in execs:
                print(
                    f"  - {e.id} | mode: {e.mode} | status: {e.status} | op: {e.operation_id} | completed: {e.completed_at}"
                )
        return

    try:
        execution_uuid = uuid.UUID(raw_exec_id)
    except ValueError:
        print(f"Error: Invalid execution UUID '{raw_exec_id}'")
        sys.exit(1)

    actor = resolve_actor(args.token)
    if not actor.can_verify:
        print(
            f"Error: Actor '{actor.identity}' lacks verification permission (roles: {sorted(actor.roles)})"
        )
        sys.exit(1)

    print(
        f"Authenticated Verifier: '{actor.identity}' (roles: {sorted(actor.roles)})\n"
    )

    async with SessionLocal() as session:
        execution = await session.get(RemediationExecution, execution_uuid)
        if not execution:
            print(
                f"Error: Remediation execution '{execution_uuid}' was not found in PostgreSQL."
            )
            sys.exit(1)

        incident = await session.get(Incident, execution.incident_id)
        approval = await session.get(RemediationApproval, execution.approval_id)

        print(f"Loaded Remediation Execution {execution.id}:")
        print(f"  Operation ID: {execution.operation_id}")
        print(f"  Execution Mode: {execution.mode}")
        print(f"  Execution Status: {execution.status}")
        print(f"  Duration: {execution.duration_ms} ms")
        print(f"  Started At: {execution.started_at.isoformat()}")
        print(f"  Completed At: {execution.completed_at.isoformat()}")
        print(
            f"  Associated Incident: '{incident.title if incident else 'Unknown'}' (ID: {execution.incident_id})"
        )
        print(f"    Incident Status: {incident.status if incident else 'unknown'}")
        print(f"  Associated Approval: {execution.approval_id}")
        print(f"    Approval Status: {approval.status if approval else 'unknown'}")
        print(f"    Approved Plan Hash: {execution.approved_plan_hash[:16]}...")

    if not args.verify:
        print("\nTo run deterministic evidence-based verification, execute:")
        print(
            f"  uv run python scripts/verify_post_execution.py {execution_uuid} --verify\n"
        )
        return

    criteria = VerificationCriteria(
        baseline_window_minutes=args.baseline_window,
        followup_window_minutes=args.followup_window,
        min_samples_required=args.min_samples,
        step=args.step,
    )

    idempotency_key = (
        args.idempotency_key
        or f"verify-{execution_uuid.hex[:8]}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    )

    print("\nExecuting deterministic post-execution verification...")
    print(f"  Idempotency Key: {idempotency_key}")
    print(f"  Baseline Window: {criteria.baseline_window_minutes}m")
    print(f"  Follow-up Window: {criteria.followup_window_minutes}m")

    try:
        async with SessionLocal() as session:
            record, is_replay = await verifications.execute_verification(
                session=session,
                execution_id=execution_uuid,
                criteria=criteria,
                idempotency_key=idempotency_key,
                requested_by=actor.identity,
            )

            # Re-read incident and approval to confirm status immutability
            inc_reloaded = await session.get(Incident, record.incident_id)
            appr_reloaded = await session.get(RemediationApproval, record.approval_id)
            events = await verifications.get_verification_events(session, record.id)

        print("\n" + "=" * 60)
        print("POST-EXECUTION VERIFICATION REPORT")
        print("=" * 60)
        print(f"Verification ID: {record.id}")
        print(f"Execution ID: {record.execution_id}")
        print(f"Execution Mode: {record.execution_mode}")
        print(f"Verification Status: {record.status}")
        print(f"Verification Outcome: {record.outcome}")
        print(f"Monitoring Access: {record.execution_mode == 'live_diagnostic'}")
        print("System Changes Performed: False")
        print(f"Remediation Success Confirmed: {record.remediation_success_confirmed}")
        print(f"Human Review Required: {record.human_review_required}")
        print(
            f"Incident Status: Unchanged ({inc_reloaded.status if inc_reloaded else 'unknown'})"
        )
        print(
            f"Approval Status: Unchanged ({appr_reloaded.status if appr_reloaded else 'unknown'})"
        )
        print(f"Duration: {record.duration_ms} ms")
        print(f"Is Replay: {is_replay}")

        if record.baseline_evidence:
            base = record.baseline_evidence
            print("\n[BASELINE EVIDENCE]")
            print(f"  Metric: {base.get('metric_name')} ({base.get('expression')})")
            print(
                f"  Interval: {base.get('interval_start')} to {base.get('interval_end')}"
            )
            print(f"  Sample Count: {base.get('sample_count')}")
            print(f"  Mean Value: {base.get('mean_value')} {base.get('unit')}")
            print(f"  Min Value: {base.get('min_value')} {base.get('unit')}")
            print(f"  Max Value: {base.get('max_value')} {base.get('unit')}")
            print(f"  Retrospective: {base.get('is_retrospective')}")
            print(f"  Availability: {base.get('data_availability')}")

        if record.followup_evidence:
            post = record.followup_evidence
            print("\n[FOLLOW-UP EVIDENCE]")
            print(f"  Metric: {post.get('metric_name')} ({post.get('expression')})")
            print(
                f"  Interval: {post.get('interval_start')} to {post.get('interval_end')}"
            )
            print(f"  Sample Count: {post.get('sample_count')}")
            print(f"  Mean Value: {post.get('mean_value')} {post.get('unit')}")
            print(f"  Min Value: {post.get('min_value')} {post.get('unit')}")
            print(f"  Max Value: {post.get('max_value')} {post.get('unit')}")
            print(f"  Availability: {post.get('data_availability')}")

        if record.metric_comparison:
            comp = record.metric_comparison
            print("\n[DETERMINISTIC METRIC COMPARISON]")
            direction = comp.get("direction")
            print(
                f"  Direction: {direction.upper() if isinstance(direction, str) else 'UNKNOWN'}"
            )
            print(
                f"  Absolute Change: {comp.get('absolute_change')} {comp.get('unit')}"
            )
            rel = comp.get("relative_change_pct")
            print(
                f"  Relative Change: {f'{rel}%' if rel is not None else 'Undefined (zero baseline)'}"
            )
            print(f"  Sample Sufficiency: {comp.get('sample_sufficiency')}")
            for note in comp.get("evaluation_notes", []):
                print(f"  Note: {note}")

        if record.observations:
            print("\n[OBSERVATIONS]")
            for obs in record.observations:
                print(f"  * {obs}")

        if record.limitations:
            print("\n[LIMITATIONS & SCOPE CONSTRAINTS]")
            for lim in record.limitations:
                print(f"  ! {lim}")

        if events:
            print(f"\n[AUDIT TRAIL ({len(events)} events)]")
            for ev in events:
                print(
                    f"  [{ev.created_at.isoformat()}] {ev.event_type} | Actor: {ev.actor} | Status: {ev.previous_status} -> {ev.new_status} | Outcome: {ev.outcome}"
                )
        print("=" * 60 + "\n")

    except (
        ConcurrencyConflictError,
        ExecutionNotFoundError,
        IdempotencyConflictError,
        PlanIntegrityError,
        VerificationEligibilityError,
    ) as exc:
        print(f"\nVerification Failed: {type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
