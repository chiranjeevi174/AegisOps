# AegisOps — Interview Demonstration & Technical Defense Guide

**Agentic SRE & Autonomous Incident Response Platform**  
*Executive Demo Sequences, Architecture Pitch, and 12 In-Depth Technical Interview Q&As*

---

## 1. Executive Summary & Value Proposition

> *"AegisOps is an enterprise-grade Agentic SRE platform that compresses Mean Time to Remediate (MTTR) from hours down to seconds by pairing stateful LangGraph agentic workflows with strict zero-trust safety invariants. Unlike naive autonomous agents that execute unconstrained shell commands, AegisOps treats AI as an advisory intelligence layer governed by mandatory human approval, immutable allowlisted execution registries, separation of duties, and automated statistical post-execution verification."*

---

## 2. 5-Minute Executive Demonstration Sequence

**Target Audience:** Engineering Managers, CTOs, Portfolio Reviewers, Recruiters  
**Objective:** Deliver a crisp, visual, end-to-end demonstration of the full incident lifecycle in 5 minutes.

| Timestamp | Phase | Screen / UI Focus | Operator Actions & Spoken Script |
|---|---|---|---|
| **00:00 - 00:45** | **System Overview** | **Overview Dashboard** (`http://localhost:5173`) | *"Welcome to AegisOps. This is an Agentic SRE command center built with an Obsidian & Copper dark theme designed to minimize cognitive fatigue during high-stress outages. On this dashboard, we monitor real-time MTTR, active incidents, Prometheus health, and safety guardrails."* |
| **00:45 - 01:30** | **Alert Ingestion** | **Incidents Page** | *"In our terminal, we inject a high-CPU degradation scenario into our microservice simulator (`curl -X POST http://127.0.0.1:8001/control/scenario/high_cpu`). Prometheus evaluates our alerting rule and dispatches a firing alert via Alertmanager. An incident appears instantly in real time on our board."* |
| **01:30 - 02:30** | **AI Investigation** | **Investigation & RCA Page** | *"We open the incident and click 'Run AI Investigation'. In the background, a LangGraph state graph queries Prometheus time-series metrics, analyzes telemetry matrices with Google Gemini, ranks candidate hypotheses, and generates a structured remediation plan cryptographically bound by a SHA-256 hash."* |
| **02:30 - 03:15** | **Separation of Duties** | **Approvals Page** | *"As Operator Dan, I request approval. But if Dan attempts to approve his own request, AegisOps immediately blocks it with HTTP 403 Forbidden. Using our persona switcher, we switch to SRE Lead Rachel, review the cryptographic plan hash, and approve the remediation."* |
| **03:15 - 04:15** | **Controlled Execution** | **Executions Page** | *"Now signed in as Operator Dan, we execute the approved remediation against our demo sandbox. AegisOps validates the operation in its immutable allowlist, snapshots degraded telemetry, calls the simulator, and resets metrics to healthy. Live metrics on the dashboard drop from 95% CPU down to 25%."* |
| **04:15 - 05:00** | **Verification & Rollback** | **Verifications & Rollbacks Pages** | *"Our post-execution verification engine runs a statistical analysis confirming telemetry recovery. Finally, to demonstrate full operational reversibility, we assess rollback readiness and execute a demo rollback, restoring the pre-incident snapshot and verifying our complete audit trail."* |

---

## 3. 10-Minute Deep Technical Walkthrough Sequence

**Target Audience:** Staff SREs, Principal Engineers, System Architects, Technical Interviewers  
**Objective:** Demonstrate architectural rigor, distributed systems fundamentals, failure modes, and code-level depth.

### Minute 1 - 2: Architecture Topology & Safety Boundary
- Open `docs/architecture_and_technical_guide.md` and display the Mermaid architecture topology.
- Explain the decoupled tiers: React 18 UI, FastAPI control plane, LangGraph agentic layer, PostgreSQL 16 persistence, Prometheus/Alertmanager observability, and isolated Telemetry Simulator.
- Emphasize the core safety invariant: **Production environments (`is_production == True`) unconditionally disallow autonomous or arbitrary shell mutations.**

### Minute 2 - 4: LangGraph Agentic Engine Deep Dive
- Show `src/aegisops/investigation/workflow.py` and explain the 4-node directed graph:
  1. `ingest_alert`: Normalizes alert metadata.
  2. `gather_telemetry`: Executes Prometheus range queries.
  3. `analyze_root_cause`: Synthesizes telemetry matrices, queries Google Gemini 1.5, ranks hypotheses with confidence scoring.
  4. `generate_remediation`: Formulates ranked actions and computes a SHA-256 cryptographic hash of the entire plan payload.
- Explain the **Graceful Fallback Mechanism**: If the Gemini API is unreachable or unconfigured, the graph falls back to deterministic expert heuristics so incident response never stalls.

### Minute 4 - 6: Cryptographic Plan Hashing & Separation of Duties
- Walk through `src/aegisops/services/approvals.py`:
  - Show how `plan_hash = hashlib.sha256(canonical_json(plan)).hexdigest()` ensures that what was approved is exactly what is executed.
  - Show the identity guard:
    ```python
    if approval.requested_by == current_user.identity:
        raise HTTPException(status_code=403, detail="Separation of duties violation...")
    ```

### Minute 6 - 8: Immutable Allowlisted Execution Engine
- Open `src/aegisops/execution/registry.py` and `src/aegisops/services/executions.py`.
- Show how operation IDs are resolved against `ALLOWLISTED_OPERATIONS` and `DEMO_REMEDIATION_OPERATIONS`.
- Emphasize that parameters are parsed with Pydantic models with strict typing, zero shell command execution, and idempotency key deduplication.

### Minute 8 - 10: Statistical Verification, Stateful Rollback & Audit Trail
- Open `src/aegisops/services/verifications.py` and show statistical comparison: baseline mean vs. followup mean, relative change calculation, and temporal coverage checks.
- Open `src/aegisops/services/rollbacks.py` and demonstrate stateful snapshot restoration on the simulator.
- Open the Audit History page in the frontend and show the immutable append-only event log with operator identities and timestamps.

---

## 4. Architecture Pitch & Technical Defense

### The "Anti-Hallucination" Defense
> **Question:** *"Why shouldn't we just let an LLM agent write and run `kubectl` or `bash` commands directly during an outage?"*
>
> **Your Defense:**  
> *"In production SRE, non-deterministic autonomous execution is catastrophic. LLMs can hallucinate arguments, misinterpret cluster contexts, delete persistent volumes, or trigger cascading failures. AegisOps separates **intelligence** from **execution**. The LLM operates purely in an advisory capacity within LangGraph, synthesizing hypotheses and selecting allowlisted actions. Execution itself is strictly deterministic: pre-registered operation definitions with Pydantic-validated parameters, mandatory human cryptographic sign-off, and zero shell interpolation. This provides the speed of agentic reasoning with the safety of aerospace fly-by-wire controls."*

---

## 5. 12 Comprehensive Technical Interview Q&As

### Q1: Why did you choose LangGraph instead of a linear script or basic LLM prompt chain?
**Answer:**  
*"Linear prompt chains assume an incident investigation follows a predictable, straight line. Real incident response is cyclic and multi-faceted. LangGraph provides a stateful Directed Acyclic/Cyclic Graph (StateGraph) with first-class state persistence, branching, and node-level isolation. Each stage (alert ingestion, telemetry gathering, root cause analysis, and remediation generation) updates a shared TypedDict state. If a stage encounters missing measurements, the graph can branch to fetch additional range queries or fall back to heuristic models. Furthermore, LangGraph enables deterministic human-in-the-loop checkpoints and replayability, which are essential for post-incident reviews."*

---

### Q2: How do you guarantee the LLM cannot hallucinate dangerous shell commands?
**Answer:**  
*"AegisOps enforces an **immutable allowlisted execution registry** (`ALLOWLISTED_OPERATIONS` and `DEMO_REMEDIATION_OPERATIONS`). The LLM never writes shell scripts, bash strings, or command-line invocations. Instead, it can only output structured JSON matching our `RemediationRecommendation` schema, referencing a predefined `operation_id` from the registry. When execution is dispatched, the backend looks up the exact Python handler registered for that operation and validates all incoming parameters against strict Pydantic schemas. If an operation ID is not in the registry, or if parameters violate type/range boundaries, execution is rejected before touching any network socket."*

---

### Q3: How is Separation of Duties enforced at both API and database levels?
**Answer:**  
*"Separation of duties is an essential regulatory requirement (SOC 2, ISO 27001). In AegisOps, when an engineer requests approval for a remediation plan, their identity is stamped as `requested_by` on the `approval_requests` record. When the `POST /api/v1/approvals/{id}/approve` endpoint is invoked, the JWT bearer token is decoded to extract the caller's identity. If `caller.identity == approval.requested_by`, the API immediately raises HTTP 403 Forbidden. At the database level, audit event records immutably record both the requester and the approver in `approval_events`, making self-approval attempts cryptographically auditable and impossible to disguise."*

---

### Q4: What happens if Google Gemini is down, rate-limited, or returns invalid JSON?
**Answer:**  
*"AegisOps is engineered for zero-dependency resilience during outages. In `src/aegisops/investigation/workflow.py`, LLM invocation is wrapped in a structured try-except block. If the Gemini API fails, times out, or returns unparseable output, the engine automatically pivots to our deterministic SRE heuristic engine (`_deterministic_root_cause_analysis`). This engine evaluates Prometheus telemetry vectors against mathematical threshold matrices (e.g. CPU > 85% + latency > 1.5s = thread pool exhaustion; error rate > 30% = downstream service outage) and produces structured, ranked remediation plans. The investigation never crashes or leaves an on-call engineer stranded."*

---

### Q5: How does the Post-Execution Verification Engine confirm remediation success?
**Answer:**  
*"Naive systems simply check whether an execution HTTP request returned code 200. AegisOps performs **statistical telemetry verification** in `src/aegisops/services/verifications.py`. When an execution finishes, the engine queries Prometheus for a baseline window (pre-remediation) and a followup window (post-remediation). It computes the statistical mean, sample count, and relative change ratio for the target metric. For example, if CPU was 95% and drops to 25%, it records a -73% relative change with direction `improving`. If metrics remain saturated, the outcome is marked `degradation_persists`, preventing false positive recovery reports."*

---

### Q6: Why is rollback readiness evaluated as "not applicable" for live diagnostics, but "applicable" for demo remediations?
**Answer:**  
*"Rollback must reflect **physical truth**. A live diagnostic or simulation execution is strictly read-only; it inspects Prometheus metrics or runs dry-run simulations. Because `system_changes_performed == False`, there is literally no infrastructure mutation to reverse. Marking rollback 'ready' for a read-only query would be deceptive. Conversely, when a demo remediation is executed against the simulator, `system_changes_performed == True`, and a state snapshot is created. The rollback readiness assessment recognizes this mutation, marks applicability as `applicable`, and enables the operator to restore the pre-incident snapshot state.

**Crucial Operational Boundary:** Demo rollback exclusively restores the previous synthetic scenario on the local evaluation simulator (`http://127.0.0.1:8001`). It does **not** perform mutations against production infrastructure, live cloud clusters, or active container orchestrators. Production rollback readiness remains strictly an advisory assessment."*

---

### Q7: In the automated E2E lifecycle test, why is the post-execution verification outcome reported as 'inconclusive' despite the simulator successfully returning to healthy?
**Answer:**  
*"This demonstrates our commitment to **empirical truth over false-positive success**. In Stage 9 of the test, the simulator API confirms it transitioned to the `healthy` scenario (CPU 25%, Latency 80ms). However, when the post-execution verification engine queries Prometheus in Stage 10 (~2 seconds later), the metric sampling window is too brief to satisfy the minimum statistical sampling coverage required for mathematical certainty. Instead of naively assuming success because an HTTP call returned 200, AegisOps adheres to a fail-closed principle: it records `outcome = inconclusive` and marks `human_review_required = True`. This guarantees that autonomous workflows cannot falsely declare mission-critical outages resolved without rigorous statistical confirmation."*

---

### Q8: How do you handle idempotency across distributed network retries?
**Answer:**  
*"Every execution, verification, and rollback request requires an `idempotency_key` (UUID or client-generated token). In `src/aegisops/services/executions.py` and `rollbacks.py`, the database enforces a `UNIQUE` constraint on `idempotency_key`. When a request arrives, the service first queries the database. If an execution with that key already exists, the service returns the existing record immediately with `is_replay = True` rather than re-executing the action. This prevents double-restarts, double-scaling, or redundant mutations if a network client retries an inflight request."*

---

### Q9: How does Prometheus Alertmanager integrate with AegisOps?
**Answer:**  
*"AegisOps exposes a webhook endpoint at `POST /api/v1/webhooks/alertmanager`. In `infrastructure/prometheus/alertmanager.yml`, Alertmanager is configured to dispatch webhook notifications to this URL. The endpoint parses the Alertmanager payload (handling alerts with status `firing` or `resolved`), extracts service labels, incident severity, annotations, and timestamps, and automatically creates or updates records in the `incidents` table. This triggers immediate real-time updates on the SRE Overview dashboard without requiring manual polling."*

---

### Q10: What is the purpose of cryptographic plan hashing (`plan_hash`)?
**Answer:**  
*"In an enterprise environment, an AI model could theoretically generate version 1 of a plan, and while an approver is reviewing it, a background process could re-run and overwrite the plan with version 2. To prevent **Time-of-Check to Time-of-Use (TOCTOU)** vulnerabilities, AegisOps computes a canonical SHA-256 hash of the entire remediation payload when the plan is generated. The approval request stores this `plan_hash`. When an operator triggers execution, the execution engine validates that the approval request's `plan_hash` matches the plan's current hash. If any parameter has been altered, execution is rejected."*

---

### Q11: How do you prevent development demo features from running in production?
**Answer:**  
*"AegisOps employs strict environment-level guards in `src/aegisops/core/config.py`. The `can_execute_demo` property returns `True` only when `ENVIRONMENT != 'production'` and `DEMO_EXECUTION_ENABLED == True`. If the application is started with `ENVIRONMENT=production`, the persona switcher API is disabled, persona endpoints return HTTP 403, and the demo remediation execution endpoint immediately rejects requests with HTTP 403 Forbidden: 'Demo execution is disabled in production environments'. Production workloads are completely shielded."*

---

### Q12: How does the Obsidian & Copper design system improve SRE cognitive efficiency?
**Answer:**  
*"During P1/P0 outages, cognitive load and visual fatigue are significant drivers of human error. Bright white themes cause eye strain, while generic blue-themed dashboards make critical alerts blend into background UI chrome. AegisOps utilizes a custom **Obsidian & Copper** dark palette: deep obsidian (#100F0D) backgrounds reduce glare, while high-contrast copper (#E58A2B) and amber (#F5A623) highlight actionable controls. Status colors are strictly reserved for operational state: emerald (#4ADE80) for healthy, amber (#FBBF24) for warnings, and rose (#FB7185) for critical incidents. This visual hierarchy guides the engineer's eye directly to anomalies and review gates."*

---

### Q13: If deploying AegisOps across multi-cluster Kubernetes, what architectural evolutions would you introduce?
**Answer:**  
*"To scale AegisOps to multi-cluster Kubernetes:
1. **Distributed Agent Workers:** Decouple LangGraph execution from the FastAPI web tier using Celery or Temporal with Redis/RabbitMQ message brokers to distribute long-running investigations across worker pods.
2. **Kubernetes CRD Operator:** Model incidents, remediation plans, and approvals as Kubernetes Custom Resource Definitions (CRDs) (e.g. `Incident.sre.aegisops.io`), allowing GitOps-based approval flows via pull requests or Kubernetes RBAC.
3. **Thanos / Cortex Federated Observability:** Replace single-node Prometheus queries with Thanos Query to execute PromQL across hundreds of heterogeneous Kubernetes clusters and cloud providers.
4. **OpenTelemetry Trace Ingestion:** Expand telemetry gathering to ingest distributed trace spans from OpenTelemetry collectors to pinpoint microservice latency bottlenecks across service meshes (Istio/Linkerd)."*
