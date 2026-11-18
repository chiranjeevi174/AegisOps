import asyncio
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from aegisops.main import app

OPERATOR_HEADERS = {"Authorization": "Bearer aegisops-dev-operator-token"}
REQUESTER_HEADERS = {"Authorization": "Bearer aegisops-dev-requester-token"}
APPROVER_HEADERS = {"Authorization": "Bearer aegisops-dev-approver-token"}
ADMIN_HEADERS = {"Authorization": "Bearer aegisops-dev-admin-token"}


async def main():
    print("=== Starting AegisOps End-to-End Workflow Verification ===")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", timeout=120.0
    ) as client:
        # Step 1: Incidents & Seed Data
        incidents_resp = await client.get("/api/v1/incidents", headers=OPERATOR_HEADERS)
        assert incidents_resp.status_code == 200, (
            f"Failed incidents list: {incidents_resp.text}"
        )
        incidents = incidents_resp.json()
        print(f"[OK] Fetched {len(incidents)} incidents from database.")
        incident_id = incidents[0]["id"]
        print(f"     Testing incident: {incident_id} - {incidents[0]['title']}")

        # Step 2: System Settings
        settings_resp = await client.get(
            "/api/v1/system/settings", headers=OPERATOR_HEADERS
        )
        assert settings_resp.status_code == 200, (
            f"Failed settings: {settings_resp.text}"
        )
        settings_data = settings_resp.json()
        assert settings_data["live_diagnostics_enabled"] is True, (
            "live_diagnostics_enabled should be True"
        )
        print(
            f"[OK] System settings verified: live_diagnostics_enabled={settings_data['live_diagnostics_enabled']}"
        )

        # Step 3: Run AI Investigation & RCA
        print(f"     Running AI Investigation & RCA on incident {incident_id}...")
        analyze_resp = await client.post(
            f"/api/v1/incidents/{incident_id}/analyze", headers=OPERATOR_HEADERS
        )
        assert analyze_resp.status_code == 200, f"Failed analyze: {analyze_resp.text}"
        analysis = analyze_resp.json()
        assert "evidence" in analysis, "Analysis missing evidence"
        assert "rca" in analysis, "Analysis missing rca"
        assert "remediation_plan" in analysis, "Analysis missing remediation_plan"
        print(
            f"[OK] AI Investigation completed. Evidences: {len(analysis['evidence'])}, Hypotheses: {len(analysis['rca']['hypotheses'])}, Actions: {len(analysis['remediation_plan']['recommended_actions'])}"
        )
        for idx, act in enumerate(analysis["remediation_plan"]["recommended_actions"]):
            print(
                f"     Action {idx + 1}: title='{act.get('title')}' action_type='{act.get('action_type')}' desc='{act.get('description')[:60]}...'"
            )

        # Pick appropriate action for CPU diagnostic
        cpu_action_idx = 1
        for idx, act in enumerate(analysis["remediation_plan"]["recommended_actions"]):
            text = f"{act.get('title', '')} {act.get('description', '')}".lower()
            if any(
                k in text for k in ["cpu", "load", "utilization", "process", "compute"]
            ):
                cpu_action_idx = idx + 1
                break

        # Step 4: Create Approval Request (Passing generated plan)
        print("     Submitting remediation plan for approval via requester...")
        approval_resp = await client.post(
            f"/api/v1/incidents/{incident_id}/approvals",
            json={"plan": analysis["remediation_plan"], "rca": analysis["rca"]},
            headers=REQUESTER_HEADERS,
        )
        assert approval_resp.status_code == 201, (
            f"Failed create approval: {approval_resp.text}"
        )
        approval = approval_resp.json()
        approval_id = approval["id"]
        print(
            f"[OK] Approval request created: ID={approval_id}, Version={approval['version']}, Status={approval['status']}, Hash={approval['plan_hash']}"
        )

        # Step 5: Self-Approval Prevention Check
        print(
            "     Verifying Separation of Duties (sre-engineer-alice cannot approve own request)..."
        )
        # Alice only has requester role so calling approve endpoint should fail
        self_approve_resp = await client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"comment": "Self approving"},
            headers=REQUESTER_HEADERS,
        )
        assert self_approve_resp.status_code == 403, (
            f"Expected 403 for unauthorized approval, got: {self_approve_resp.status_code}"
        )
        print(
            "[OK] Requester approval blocked with HTTP 403 as required by safety invariants."
        )

        # Step 6: Legitimate Approval by sre-lead-charlie
        print(
            "     Approving remediation plan via authorized approver (sre-lead-charlie)..."
        )
        legit_approve_resp = await client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"comment": "Approved following SRE runbook review"},
            headers=APPROVER_HEADERS,
        )
        assert legit_approve_resp.status_code == 200, (
            f"Approval failed: {legit_approve_resp.text}"
        )
        approved_data = legit_approve_resp.json()
        assert approved_data["status"] == "approved"
        print(
            f"[OK] Plan approved successfully: status={approved_data['status']}, decided_by={approved_data['decided_by']}"
        )

        # Step 7: Executions Engine - Simulation Dry-Run
        print(f"     Running Dry-Run Simulation on action #{cpu_action_idx}...")
        sim_resp = await client.post(
            "/api/v1/executions/simulate",
            json={
                "approval_id": approval_id,
                "incident_id": incident_id,
                "operation_id": "inspect_cpu_metrics",
                "recommendation_index": cpu_action_idx,
                "idempotency_key": f"verify-sim-{UUID(int=101)}",
                "parameters": {},
            },
            headers=OPERATOR_HEADERS,
        )
        assert sim_resp.status_code == 201, f"Simulation failed: {sim_resp.text}"
        sim_data = sim_resp.json()
        assert sim_data["mode"] == "simulation"
        assert sim_data["status"] == "simulated"
        print(
            f"[OK] Simulation completed successfully: mode={sim_data['mode']}, status={sim_data['status']}, duration={sim_data['duration_ms']}ms"
        )

        # Step 8: Executions Engine - Read-Only Live Diagnostic
        print(
            f"     Running Live Read-Only Diagnostic against Prometheus on action #{cpu_action_idx}..."
        )
        diag_resp = await client.post(
            "/api/v1/executions/diagnose",
            json={
                "approval_id": approval_id,
                "incident_id": incident_id,
                "operation_id": "inspect_cpu_metrics",
                "recommendation_index": cpu_action_idx,
                "idempotency_key": f"verify-diag-{UUID(int=102)}",
                "parameters": {},
            },
            headers=OPERATOR_HEADERS,
        )
        assert diag_resp.status_code == 201, (
            f"Diagnostic failed: diag_resp={diag_resp.text}"
        )
        diag_data = diag_resp.json()
        assert diag_data["mode"] == "live_diagnostic"
        assert diag_data["status"] == "diagnosed"
        assert diag_data["system_changes_performed"] is False
        print(
            f"[OK] Live diagnostic completed successfully: mode={diag_data['mode']}, status={diag_data['status']}, metric={diag_data['diagnostic_result']['metric_identifier']}, measurements={len(diag_data['diagnostic_result']['measurements'])}"
        )

        # Step 9: Post-Remediation Verification
        print("     Running Verification Assessment...")
        verif_resp = await client.post(
            f"/api/v1/executions/{diag_data['id']}/verifications",
            json={
                "idempotency_key": f"verify-verif-{UUID(int=103)}",
            },
            headers=OPERATOR_HEADERS,
        )
        assert verif_resp.status_code == 201, f"Verification failed: {verif_resp.text}"
        verif_data = verif_resp.json()
        print(
            f"[OK] Verification assessment created: outcome={verif_data['outcome']}, status={verif_data['status']}"
        )

        # Step 10: Rollback Assessment & Simulation
        print("     Running Rollback Assessment...")
        rb_resp = await client.post(
            f"/api/v1/executions/{diag_data['id']}/rollback-assessments",
            json={
                "idempotency_key": f"verify-rb-{UUID(int=104)}",
            },
            headers=OPERATOR_HEADERS,
        )
        assert rb_resp.status_code == 201, f"Rollback failed: {rb_resp.text}"
        rb_data = rb_resp.json()
        print(
            f"[OK] Rollback assessment created: ID={rb_data['id']}, readiness={rb_data['readiness_status']}, system_changes={rb_data['system_changes_performed']}"
        )

        # Step 11: Unified Audit Trail
        print("     Querying Unified Audit Trail...")
        audit_resp = await client.get(
            "/api/v1/audit/events?limit=10", headers=OPERATOR_HEADERS
        )
        assert audit_resp.status_code == 200, f"Audit query failed: {audit_resp.text}"
        audit_events = audit_resp.json()
        print(f"[OK] Audit log contains {len(audit_events)} recent events.")

    print("\n=== ALL WORKFLOWS FULLY AUDITED, REPAIRED & VERIFIED END-TO-END! ===")


if __name__ == "__main__":
    asyncio.run(main())
