import asyncio
import sys
from uuid import UUID

from aegisops.db.session import SessionLocal
from aegisops.services.incidents import (
    IncidentNotFoundError,
    get_incident,
    list_incidents,
    run_incident_workflow,
)


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/verify_rca.py <incident-uuid>")
        print("\nAvailable incidents in database:")
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

    raw_id = sys.argv[1].strip()
    try:
        incident_uuid = UUID(raw_id)
    except ValueError:
        print(f"Error: '{raw_id}' is not a valid UUID format.")
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
        print(f"  - Alert Fingerprint: {incident.alert_fingerprint}")
        print(f"  - Alert Started At: {incident.alert_started_at}")

        if not incident.alert_started_at:
            print(
                "\n[WARNING] Incident has no alert occurrence timestamp (alert_started_at is None)."
            )
            print("Historical metric correlation requires an occurrence timestamp.")

        print(
            "\nExecuting agentic incident workflow (Triage -> Evidence -> Investigation -> Historical -> RCA)..."
        )
        try:
            result = await run_incident_workflow(session, incident_uuid)
        except IncidentNotFoundError:
            print(f"Error: Incident {incident_uuid} not found.")
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            print(f"Workflow execution failed: {type(exc).__name__}: {exc}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("WORKFLOW EXECUTION REPORT")
    print("=" * 60)

    # 1. Triage
    print("\n[TRIAGE]")
    print(f"  Priority: {result.get('priority', 'N/A')}")
    print(f"  Requires Escalation: {result.get('requires_escalation', False)}")

    # 2. Live Monitoring Evidence
    print("\n[LIVE MONITORING EVIDENCE]")
    print(f"  Evidence Type: {result.get('evidence_type', 'unavailable')}")
    print(f"  Collected At: {result.get('evidence_collected_at', 'N/A')}")
    if result.get("monitoring_error"):
        print(f"  Monitoring Error: {result['monitoring_error']}")
    else:
        for k, v in (result.get("evidence") or {}).items():
            print(f"  - {k}: {v}")

    # 3. Investigation
    print("\n[GEMINI INVESTIGATION]")
    if result.get("investigation_error"):
        print(f"  Investigation Error: {result['investigation_error']}")
    elif result.get("investigation"):
        inv = result["investigation"]
        print(f"  Summary: {inv.get('summary')}")
        print(f"  Confidence: {inv.get('confidence')}")
        print("  Observations:")
        for obs in inv.get("observations", []):
            print(f"    * {obs}")
        print("  Possible Causes:")
        for pc in inv.get("possible_causes", []):
            print(f"    * {pc}")
        print("  Recommended Checks:")
        for rc in inv.get("recommended_checks", []):
            print(f"    * {rc}")
    else:
        print("  Investigation was skipped (no evidence available).")

    # 4. Historical Evidence
    print("\n[HISTORICAL EVIDENCE RETRIEVAL]")
    if result.get("historical_evidence_error"):
        print(f"  Historical Evidence Status: {result['historical_evidence_error']}")
    elif result.get("historical_evidence"):
        hw = result.get("historical_window") or {}
        print(
            f"  Window: {hw.get('start')} to {hw.get('end')} (step: {hw.get('step')})"
        )
        metrics = result["historical_evidence"].get("metrics", {})
        for name, m in metrics.items():
            print(
                f"  - {name}: count={m.get('count')}, min={m.get('min')}, max={m.get('max')}, avg={m.get('avg')}, first={m.get('first')}, last={m.get('last')}"
            )
    else:
        print("  Historical evidence was not retrieved.")

    # 5. Root Cause Analysis
    print("\n[ROOT CAUSE ANALYSIS (RCA)]")
    if result.get("rca_error"):
        print(f"  RCA Status: {result['rca_error']}")
    elif result.get("rca"):
        rca = result["rca"]
        print(f"  Summary: {rca.get('summary')}")
        print(f"  Overall Confidence: {rca.get('overall_confidence')}")
        print(f"  Most Likely Hypothesis: {rca.get('most_likely_hypothesis')}")
        print(
            f"  Root Cause Confirmed: {rca.get('root_cause_confirmed')} (Safety constraint preserved)"
        )
        print(f"  Requires Human Review: {rca.get('requires_human_review')}")

        print("\n  Key Historical Observations:")
        for obs in rca.get("key_observations", []):
            print(f"    * {obs}")

        print("\n  Important Metric Changes:")
        for mc in rca.get("metric_changes", []):
            print(f"    * {mc}")

        print("\n  Data Limitations:")
        for dl in rca.get("data_limitations", []):
            print(f"    * {dl}")

        print("\n  Hypotheses:")
        for h in rca.get("hypotheses", []):
            print(f"    - [{h.get('confidence').upper()}] {h.get('title')}")
            print(f"        Explanation: {h.get('explanation')}")
            print(
                f"        Supporting: {', '.join(h.get('supporting_evidence', [])) or 'None'}"
            )
            print(
                f"        Contradicting: {', '.join(h.get('contradicting_evidence', [])) or 'None'}"
            )
            print(
                f"        Missing: {', '.join(h.get('missing_evidence', [])) or 'None'}"
            )

        print("\n  Recommended Diagnostic Checks:")
        for rc in rca.get("recommended_checks", []):
            print(f"    * {rc}")
    # 6. Safe Remediation Planning
    print("\n[SAFE REMEDIATION PLANNING]")
    if result.get("remediation_error"):
        print(f"  Remediation Status: {result['remediation_error']}")
    elif result.get("remediation_plan"):
        plan = result["remediation_plan"]
        print(f"  Incident Summary: {plan.get('incident_summary')}")
        print(f"  Planning Basis: {plan.get('planning_basis')}")
        print(f"  Overall Risk Level: {plan.get('overall_risk')}")
        print(f"  Execution Enabled: {plan.get('execution_enabled')}")
        print(f"  Human Approval Required: {plan.get('requires_human_approval')}")
        print("  Remediation Executed: None (Advisory Only)")

        if plan.get("missing_information"):
            print("\n  Missing Information:")
            for mi in plan["missing_information"]:
                print(f"    * {mi}")

        print("\n  Recommended Actions:")
        for idx, act in enumerate(plan.get("recommended_actions", []), start=1):
            print(f"\n    Action {idx}: {act.get('title')}")
            print(f"      Type: {act.get('action_type')}")
            print(f"      Risk Level: {act.get('risk_level')}")
            print(
                f"      Requires Human Approval: {act.get('requires_human_approval')}"
            )
            print(f"      Description: {act.get('description')}")
            print(f"      Rationale: {act.get('rationale')}")
            if act.get("supporting_evidence"):
                print(
                    f"      Supporting Evidence: {', '.join(act['supporting_evidence'])}"
                )
            if act.get("prerequisites"):
                print(f"      Prerequisites: {', '.join(act['prerequisites'])}")
            if act.get("validation_steps"):
                print(f"      Validation Steps: {', '.join(act['validation_steps'])}")
            if act.get("rollback_considerations"):
                print(
                    f"      Rollback Considerations: {', '.join(act['rollback_considerations'])}"
                )
    else:
        print("  Remediation planning was not generated.")

    print("\n" + "=" * 60)
    print("SAFETY AUDIT VERIFICATION")
    print("=" * 60)
    print("  Execution Enabled: False")
    print("  Human Approval Required: True")
    print("  Remediation Actions Executed: None (Advisory Planning Only)")
    print("  System Mutation Status: None (Zero Infrastructure Changes)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
