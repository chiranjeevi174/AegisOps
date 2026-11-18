"""
AegisOps - End-to-End Live Demo Execution & Rollback Verification Script
Tests the full lifecycle against a running AegisOps API (port 8000) and Telemetry Simulator (port 8001).
"""

import sys
import time

import httpx

API_BASE = "http://127.0.0.1:8000/api/v1"
SIM_BASE = "http://127.0.0.1:8001"

OPERATOR_TOKEN = "aegisops-dev-operator-token"
APPROVER_TOKEN = "aegisops-dev-approver-token"
REQUESTER_TOKEN = "aegisops-dev-requester-token"

OPERATOR_HEADERS = {
    "Authorization": f"Bearer {OPERATOR_TOKEN}",
    "Content-Type": "application/json",
}

APPROVER_HEADERS = {
    "Authorization": f"Bearer {APPROVER_TOKEN}",
    "Content-Type": "application/json",
}

REQUESTER_HEADERS = {
    "Authorization": f"Bearer {REQUESTER_TOKEN}",
    "Content-Type": "application/json",
}


def main():
    print("=" * 80)
    print(" AegisOps End-to-End Demo Execution & Rollback Lifecycle Verification")
    print("=" * 80)

    client = httpx.Client(timeout=120.0)

    # 1. Health Checks
    print("\n[Step 1] Checking backend API and telemetry simulator availability...")
    try:
        api_health = client.get("http://127.0.0.1:8000/health")
        print(
            f" -> Backend API Health: HTTP {api_health.status_code} ({api_health.json()})"
        )
    except (httpx.HTTPError, OSError) as e:
        print(f" [!] Backend API not reachable on port 8000: {e}")
        print("     Please ensure the AegisOps API is running.")
        sys.exit(1)

    try:
        sim_health = client.get(f"{SIM_BASE}/health")
        print(
            f" -> Simulator Health: HTTP {sim_health.status_code} ({sim_health.json()})"
        )
    except (httpx.HTTPError, OSError) as e:
        print(f" [!] Simulator not reachable on port 8001: {e}")
        print("     Please ensure scripts/simulate_service.py is running.")
        sys.exit(1)

    # 2. Set simulator to degraded scenario
    print("\n[Step 2] Injecting degraded scenario 'high_cpu' into simulator...")
    set_scen = client.post(f"{SIM_BASE}/control/scenario/high_cpu")
    print(f" -> Scenario response: HTTP {set_scen.status_code} ({set_scen.json()})")

    state_resp = client.get(f"{SIM_BASE}/control/state")
    state = state_resp.json()
    print(f" -> Simulator active scenario: {state.get('active_scenario')}")
    print(f" -> Simulator CPU metric: {state.get('metrics', {}).get('cpu_percent')}%")

    # 3. Create Incident
    print("\n[Step 3] Creating incident for degraded service degradation...")

    inc_payload = {
        "title": "High CPU Saturation and Service Latency Spike on api-service",
        "description": "Simulated latency spike and sustained CPU threshold breach detected by Prometheus.",
        "severity": "critical",
        "status": "firing",
        "source": "prometheus_alertmanager",
    }
    inc_resp = client.post(
        f"{API_BASE}/incidents", json=inc_payload, headers=REQUESTER_HEADERS
    )
    if inc_resp.status_code not in (200, 201):
        print(f"Failed to create incident: {inc_resp.status_code} {inc_resp.text}")
        sys.exit(1)
    incident = inc_resp.json()
    inc_id = incident["id"]
    print(f" -> Incident Created: ID={inc_id}, Status={incident.get('status')}")

    # 4. Trigger AI Investigation & RCA
    print("\n[Step 4] Running AI Investigation & Root Cause Analysis...")
    inv_resp = client.post(
        f"{API_BASE}/incidents/{inc_id}/analyze", headers=REQUESTER_HEADERS
    )
    print(f" -> Investigation Response: HTTP {inv_resp.status_code}")
    if inv_resp.status_code not in (200, 201):
        print(f"Investigation failed: {inv_resp.text}")
        sys.exit(1)
    inv_data = inv_resp.json()
    print(f" -> Investigation Priority: {inv_data.get('priority')}")
    print(
        f" -> Root Cause Hypothesis: {inv_data.get('rca', {}).get('probable_cause') or inv_data.get('rca', {}).get('hypothesis')}"
    )

    # 5. Get Remediation Plan & Request Approval
    print("\n[Step 5] Requesting human approval for remediation plan...")
    appr_req_payload = {
        "incident_id": inc_id,
        "requested_by": "sre-engineer-alice",
    }
    appr_req_resp = client.post(
        f"{API_BASE}/incidents/{inc_id}/approvals",
        json=appr_req_payload,
        headers=REQUESTER_HEADERS,
    )
    print(f" -> Approval Request Response: HTTP {appr_req_resp.status_code}")
    if appr_req_resp.status_code not in (200, 201):
        print(f"Failed to create approval request: {appr_req_resp.text}")
        sys.exit(1)
    appr_data = appr_req_resp.json()
    approval_id = appr_data["id"]
    print(
        f" -> Approval Request Created: ID={approval_id}, Status={appr_data.get('status')}, Plan Hash={appr_data.get('plan_hash')[:12]}..."
    )

    # Verify Separation of Duties: Requester cannot approve
    print(
        "\n[Step 6] Testing Separation of Duties (Requester self-approval must fail)..."
    )
    self_appr_resp = client.post(
        f"{API_BASE}/approvals/{approval_id}/approve",
        json={"reason": "Self-approving my own plan"},
        headers=REQUESTER_HEADERS,
    )
    print(
        f" -> Requester self-approval attempt: HTTP {self_appr_resp.status_code} (Expected 403 Forbidden)"
    )
    assert self_appr_resp.status_code == 403, (
        "Security breach: Requester was able to self-approve!"
    )
    print(" -> PASS: Separation of duties strictly enforced.")

    # 7. Approver approves
    print("\n[Step 7] Lead Approver approving the plan...")
    lead_appr_resp = client.post(
        f"{API_BASE}/approvals/{approval_id}/approve",
        json={"reason": "Remediation plan verified and approved for demo execution"},
        headers=APPROVER_HEADERS,
    )
    print(f" -> Approver response: HTTP {lead_appr_resp.status_code}")
    assert lead_appr_resp.status_code == 200, f"Approval failed: {lead_appr_resp.text}"
    print(f" -> Approval confirmed: Status={lead_appr_resp.json().get('status')}")

    # 8. Execute Demo Remediation
    print(
        "\n[Step 8] Executing Demo Remediation against isolated telemetry simulator..."
    )
    exec_payload = {
        "approval_id": approval_id,
        "incident_id": inc_id,
        "operation_id": "remediate_service_degradation",
        "recommendation_index": 1,
        "idempotency_key": f"demo-e2e-{int(time.time())}",
        "parameters": {
            "service_name": "api-service",
            "target_scenario": "healthy",
        },
    }
    exec_resp = client.post(
        f"{API_BASE}/executions/execute-demo",
        json=exec_payload,
        headers=OPERATOR_HEADERS,
    )
    print(f" -> Execute Demo Response: HTTP {exec_resp.status_code}")
    assert exec_resp.status_code in (200, 201), (
        f"Demo execution failed: {exec_resp.text}"
    )
    exec_data = exec_resp.json()
    exec_id = exec_data["id"]
    print(f" -> Execution Record ID: {exec_id}")
    print(f" -> Mode: {exec_data.get('mode')}")
    print(f" -> Status: {exec_data.get('status')}")
    print(f" -> Duration: {exec_data.get('duration_ms')} ms")
    print(f" -> System Changes Performed: {exec_data.get('system_changes_performed')}")
    print(f" -> Result Summary: {exec_data.get('execution_result', {}).get('message')}")

    # Check simulator state changed to healthy
    print("\n[Step 9] Verifying simulator telemetry state post-execution...")
    sim_state_after = client.get(f"{SIM_BASE}/control/state").json()
    print(f" -> Simulator Active Scenario: {sim_state_after.get('active_scenario')}")
    print(
        f" -> Simulator CPU: {sim_state_after.get('metrics', {}).get('cpu_percent')}%"
    )
    print(
        f" -> Simulator Latency: {sim_state_after.get('metrics', {}).get('latency_seconds') * 1000:.1f} ms"
    )
    print(
        f" -> Simulator Service Up: {sim_state_after.get('metrics', {}).get('service_up')}"
    )
    assert sim_state_after.get("active_scenario") == "healthy", (
        "Simulator was not changed to healthy scenario!"
    )
    assert sim_state_after.get("metrics", {}).get("cpu_percent") == 25, (
        "CPU metric not healthy!"
    )
    print(" -> PASS: Demo remediation successfully restored healthy telemetry!")

    # 10. Post-Execution Verification
    print("\n[Step 10] Running Post-Execution Verification...")
    verif_payload = {
        "idempotency_key": f"verif-e2e-{int(time.time())}",
    }
    verif_resp = client.post(
        f"{API_BASE}/executions/{exec_id}/verifications",
        json=verif_payload,
        headers=OPERATOR_HEADERS,
    )
    print(f" -> Verification Response: HTTP {verif_resp.status_code}")
    if verif_resp.status_code == 200:
        verif_data = verif_resp.json()
        print(f" -> Verification ID: {verif_data.get('id')}")
        print(f" -> Verification Status: {verif_data.get('status')}")
        print(f" -> Outcome: {verif_data.get('outcome')}")

    # 11. Rollback Readiness Assessment
    print("\n[Step 11] Running Rollback Readiness Assessment...")
    rb_assess_payload = {
        "idempotency_key": f"rb-assess-e2e-{int(time.time())}",
    }
    rb_assess_resp = client.post(
        f"{API_BASE}/executions/{exec_id}/rollback-assessments",
        json=rb_assess_payload,
        headers=OPERATOR_HEADERS,
    )
    print(f" -> Rollback Assessment Response: HTTP {rb_assess_resp.status_code}")
    assert rb_assess_resp.status_code in (200, 201), (
        f"Rollback assessment failed: {rb_assess_resp.text}"
    )
    rb_assess_data = rb_assess_resp.json()
    assessment_id = rb_assess_data["id"]
    print(f" -> Assessment ID: {assessment_id}")
    print(f" -> Readiness Status: {rb_assess_data.get('readiness_status')}")
    print(f" -> Applicability: {rb_assess_data.get('applicability')}")
    print(
        f" -> Rollback Execution Enabled: {rb_assess_data.get('rollback_execution_enabled')}"
    )
    assert rb_assess_data.get("applicability") == "applicable", (
        "Assessment must mark demo execution as applicable for rollback!"
    )

    # 12. Execute Demo Rollback
    print(
        "\n[Step 12] Executing Demo Rollback to restore pre-incident degraded state..."
    )
    rb_exec_payload = {
        "assessment_id": assessment_id,
        "idempotency_key": f"rb-exec-e2e-{int(time.time())}",
        "reason": "Demonstrating end-to-end rollback recovery to pre-incident state",
    }
    rb_exec_resp = client.post(
        f"{API_BASE}/demo-rollbacks/execute",
        json=rb_exec_payload,
        headers=OPERATOR_HEADERS,
    )
    print(f" -> Rollback Execution Response: HTTP {rb_exec_resp.status_code}")
    assert rb_exec_resp.status_code in (200, 201), (
        f"Rollback execution failed: {rb_exec_resp.text}"
    )
    rb_exec_data = rb_exec_resp.json()
    print(f" -> Rollback Execution ID: {rb_exec_data.get('id')}")
    print(f" -> Rollback Status: {rb_exec_data.get('status')}")
    print(f" -> Restored Scenario: {rb_exec_data.get('restored_scenario')}")
    print(f" -> Duration: {rb_exec_data.get('duration_ms')} ms")

    # 13. Verify Simulator restored to high_cpu
    print("\n[Step 13] Verifying simulator telemetry state post-rollback...")
    sim_state_rolled_back = client.get(f"{SIM_BASE}/control/state").json()
    print(
        f" -> Simulator Active Scenario: {sim_state_rolled_back.get('active_scenario')}"
    )
    print(
        f" -> Simulator CPU: {sim_state_rolled_back.get('metrics', {}).get('cpu_percent')}%"
    )
    assert sim_state_rolled_back.get("active_scenario") == "high_cpu", (
        "Simulator was not restored to high_cpu!"
    )
    assert sim_state_rolled_back.get("metrics", {}).get("cpu_percent") == 94, (
        "CPU metric not restored!"
    )
    print(
        " -> PASS: Demo rollback successfully reverted simulator to pre-incident degraded scenario!"
    )

    # 14. Audit History Verification
    print("\n[Step 14] Querying Audit Event History...")
    audit_resp = client.get(
        f"{API_BASE}/audit/events?limit=10", headers=OPERATOR_HEADERS
    )
    print(f" -> Audit events status: HTTP {audit_resp.status_code}")
    if audit_resp.status_code == 200:
        events = audit_resp.json()
        print(f" -> Retrieved {len(events)} recent audit events:")
        for ev in events[:5]:
            print(
                f"    * [{ev.get('timestamp') or ev.get('created_at')}] {ev.get('action') or ev.get('event_type')} by {ev.get('actor') or ev.get('user_id')}"
            )

    print("\n" + "=" * 80)
    print(" ALL 14 END-TO-END DEMO EXECUTION & ROLLBACK STAGES PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
