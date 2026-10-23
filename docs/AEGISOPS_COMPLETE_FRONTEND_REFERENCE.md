# AEGISOPS — COMPLETE FRONTEND FEATURE INVENTORY AND OPERATIONAL REFERENCE

**Document Version:** 1.0.0
**Classification:** Technical Product Reference & SRE Operations Guide
**System Under Evaluation:** AegisOps — Agentic SRE & Autonomous Incident Response Platform
**Target Environment:** Local Full-Stack Deployment (Frontend: `http://localhost:5173`, Backend: `http://localhost:8000`, Prometheus: `http://localhost:9090`, Alertmanager: `http://localhost:9093`, Grafana: `http://localhost:3000`)
**Source Repository:** `D:\PROJECTS\Agentic SRE and Autonomous Incident Response Platform AegisOps`

---

## 1. Executive & Application Overview

### 1.1 What AegisOps Is
AegisOps is an **Agentic Site Reliability Engineering (SRE) and Autonomous Incident Response Platform** engineered to bridge observability alerts with deterministic, safety-bounded remediation planning. Built with a modern TypeScript/React 18 frontend and a Python/FastAPI/SQLAlchemy asynchronous backend, AegisOps ingests production telemetry and alert notifications, orchestrates multi-agent AI investigations via LangGraph and Google Gemini, constructs safety-validated remediation plans, and gates all actions behind cryptographic human-in-the-loop approvals.

### 1.2 Operational Problems Addressed
1. **Alert Fatigue & Context Fragmentation:** On-call SREs are frequently overwhelmed by noisy Alertmanager streams across microservices without consolidated baseline telemetry or historical context.
2. **Slow Mean Time to Detect/Diagnose (MTTD):** Manually correlating Prometheus metrics, identifying root causes, and formulating multi-step recovery runbooks takes critical minutes during major service degradations.
3. **The "Autonomous AI Risk":** Unchecked autonomous agents executing arbitrary scripts (`rm -rf`, raw SSH commands, database mutations) in production environments present an unacceptable catastrophic failure risk.
4. **Lack of Remediation Auditability:** Ad-hoc terminal diagnostics and manual hotfixes lack verifiable cryptographic binding, version tracking, post-execution verification, and rollback prerequisites.

### 1.3 Target Audience & Personas
* **Site Reliability Engineers (SREs):** Triage incoming alerts, trigger agentic root-cause investigations, evaluate proposed remediation hypotheses, and run non-mutating live diagnostics.
* **Incident Commanders / SRE Leads:** Formally inspect advisory remediation plans, verify risk levels, and authorize or reject execution requests.
* **Platform Operations & DevOps Engineers:** Maintain allowlisted operation definitions, monitor Prometheus scrape targets, and verify rollback readiness.
* **Compliance & Security Auditors:** Review append-only, tamper-resistant event logs tracing every actor, decision, hash, and status transition.

### 1.4 The Agentic AI Architecture
AegisOps employs a **state-graph agentic architecture** orchestrated via `langgraph`. The AI is not a single unstructured chatbot; rather, it is divided into discrete, specialized agent nodes with strictly typed inputs and outputs:
* **Triage Agent:** Deterministically calculates priority (P1–P4) based on incident severity and source.
* **Evidence Collection Node:** Programmatically queries the Prometheus HTTP API to capture instantaneous metric snapshots (`aegisops_sim_service_up`, `aegisops_sim_cpu_usage_ratio`, `aegisops_sim_latency_seconds`, `aegisops_sim_error_rate_ratio`).
* **Historical Evidence Node:** Extracts a multi-sample historical time-series window prior to alert firing.
* **Investigation Agent:** Evaluates telemetry trends and formulates structured observations and recommended diagnostic checks.
* **RCA (Root Cause Analysis) Agent:** Powers multi-hypothesis deductive reasoning via Gemini (`gemini-3.5-flash-lite`), explicitly classifying evidence into **supporting**, **contradicting**, and **missing** categories.
* **Remediation Planning Agent:** Constructs structured, step-by-step remediation proposals mapped to low-risk allowlisted operations.
* **Safety Validator Node:** A deterministic Python node that runs *after* Gemini to strictly enforce security invariants (disabling autonomous execution flags, requiring human approval, validating risk tiers).

### 1.5 What Decisions Remain Deterministic
* **Safety Invariant Enforcement:** `execution_enabled` is hardcoded to `False`; `requires_human_approval` is hardcoded to `True`. The LLM cannot override these flags.
* **Operation Allowlist Enforcement:** Executions can only invoke pre-registered, allowlisted operation IDs (`inspect_service_health`, `inspect_cpu_metrics`, `inspect_latency_metrics`, `inspect_error_rate`, `review_service_configuration`). Banned commands (`shell`, `bash`, `powershell`, `rm`, `ssh`) fail closed.
* **Cryptographic Plan Hashing:** The SHA-256 hash of the normalized plan JSON is deterministically computed and verified before every decision and execution.
* **Separation of Duties:** Self-approval is deterministically prohibited by the backend when `enforce_separation_of_duties` is active.
* **Statistical Verification:** Post-execution verification uses strict mathematical comparison with explicit epsilon tolerance ($\epsilon = 0.01$).

### 1.6 What Actions Require Human Approval
* **Plan Authorization:** Transitioning any proposed remediation plan from `pending` to `approved` requires an explicit, authenticated decision by an actor holding the `approver` or `admin` role.
* **Execution Invocation:** Triggering any dry-run simulation or read-only live diagnostic requires explicit operator action with an approved plan UUID and explicit confirmation checkboxes.
* **Plan Revision / Rejection:** Rejecting or requesting changes on a plan requires mandatory human documentation of reasons.

### 1.7 Operational Boundaries: What the Platform Can and Cannot Execute
| Capability | Platform Status | Architectural Explanation |
| :--- | :--- | :--- |
| **AI Remediation Recommendations** | **Supported (Advisory Only)** | Generated by Gemini and validated by Python rules. Displayed on frontend as advisory suggestions. |
| **Dry-Run Simulation Mode** | **Supported** | Simulates operation duration and synthetic observations in a sandbox without network access. |
| **Live Diagnostic Mode** | **Supported (Read-Only)** | Queries live Prometheus metric APIs to inspect live telemetry. Strictly non-mutating. |
| **Actual Infrastructure Mutation** | **Intentionally Disabled** | No SSH, Kubernetes pod restart, container kill, configuration mutation, or shell execution is implemented. |
| **Rollback Execution** | **Intentionally Disabled** | Rollback readiness evaluates prerequisites and hypothetical restoration only; no real rollback is performed. |

---

## 2. End-to-End Operational Architecture & Flow

```
+----------------------------------------------------------------------------------------------------+
|                                    1. TELEMETRY & ALERT INGESTION                                  |
|                                                                                                    |
|  [Telemetry Simulator] ===(Prometheus Scrape)===> [Prometheus Server] ===(Alerts)===> [Alertmanager]|
|       (Port 8001)                                      (Port 9090)                         (Port 9093)      |
|                                                                                                 |  |
|                                                                                                 v  |
|                                                     [FastAPI Alertmanager Webhook Ingestion] <----+|
|                                                               (POST /api/v1/webhooks/alertmanager)  |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v (Automatic Database Record Creation)
+----------------------------------------------------------------------------------------------------+
|                                    2. INCIDENT STORAGE & RETRIEVAL                                 |
|                                                                                                    |
|       [PostgreSQL Database: 'incidents' table] <=====> [Frontend Incident Management (/incidents)]   |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v (Explicit Operator Click: "Run AI Investigation")
+----------------------------------------------------------------------------------------------------+
|                                    3. LANGGRAPH MULTI-AGENT WORKFLOW                               |
|                                                                                                    |
|   START --> [Triage Node]                                                                          |
|                |                                                                                   |
|                v                                                                                   |
|         [Collect Evidence] ---> (If error / no data) -----------------------------------> [END]   |
|                |                                                                             ^     |
|                v (If telemetry valid)                                                        |     |
|         [Investigate Node]                                                                   |     |
|                |                                                                             |     |
|                v                                                                             |     |
|   [Collect Historical Evidence] ---> (If error / no range data) -----------------------------+     |
|                |                                                                             |     |
|                v (If time-series valid)                                                      |     |
|   [Root Cause Analysis Node (Gemini)] ---> (If error) ---------------------------------------+     |
|                |                                                                             |     |
|                v (If hypotheses generated)                                                   |     |
|   [Remediation Planning Node (Gemini)]                                                       |     |
|                |                                                                             |     |
|                v                                                                             |     |
|   [Deterministic Safety Validation Node] ---------------------------------------------------+     |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v (LangGraph Ends: Returns Advisory JSON Result)
+----------------------------------------------------------------------------------------------------+
|                                    4. HUMAN APPROVAL GATEWAY LIFECYCLE                             |
|                                                                                                    |
|   Operator clicks "Create Approval Request" ===> [POST /api/v1/incidents/{id}/approvals]           |
|                                                              |                                     |
|                                                              v                                     |
|                                            [New Approval Record Created: Version N]                |
|                                            [SHA-256 Plan Hash Computed & Locked]                   |
|                                            [Status: PENDING | Supersedes Old Version]              |
|                                                              |                                     |
|                                                              v                                     |
|                            [Different Approver Reviews in /approvals Gateway]                      |
|                                     /                        |                       \             |
|                                    /                         |                        \            |
|                           (Approve)                      (Reject)              (Request Revision)  |
|                               v                              v                          v          |
|                      [Status: APPROVED]             [Status: REJECTED]       [Status: REVISION_REQ]|
+----------------------------------------------------------------------------------------------------+
                                | (Only if APPROVED)
                                v
+----------------------------------------------------------------------------------------------------+
|                                    5. CONTROLLED EXECUTION ENGINE                                  |
|                                                                                                    |
|   Operator navigates to /executions ===> Selects Approved Plan Version & Allowlisted Operation     |
|                                     /                                        \                     |
|                                    /                                          \                    |
|                        (Dry-Run Simulation)                          (Live Read-Only Diagnostic)   |
|                                   v                                                    v           |
|                 [POST /api/v1/executions/simulate]                    [POST /api/v1/executions/diagnose]|
|                 - Synthetic sandbox duration                          - Queries Prometheus HTTP API |
|                 - Zero network/system access                          - Strict read-only telemetry  |
|                                   \                                                    /           |
|                                    v                                                  v            |
|                            [Execution Record Stored: 'simulated' or 'diagnosed']                   |
|                            [Execution Events Recorded to Append-Only Audit Trail]                  |
+----------------------------------------------------------------------------------------------------+
                                |
                                v
+----------------------------------------------------------------------------------------------------+
|                                    6. POST-EXECUTION VERIFICATION                                  |
|                                                                                                    |
|   Operator clicks "Create Verification" ===> [POST /api/v1/executions/{id}/verifications]          |
|   - Baseline Observation Window (e.g. 15m) vs Follow-up Observation Window (e.g. 15m)              |
|   - Statistical comparison with epsilon tolerance (e = 0.01)                                       |
|   - Classifies outcome: DIAGNOSTIC_VERIFIED | NOT_APPLICABLE | INCONCLUSIVE | FAILED                |
|   - Explicit Invariant: remediation_success_confirmed = False                                      |
+----------------------------------------------------------------------------------------------------+
                                |
                                v
+----------------------------------------------------------------------------------------------------+
|                                    7. ROLLBACK READINESS & SIMULATION                              |
|                                                                                                    |
|   Operator clicks "Assess Rollback Readiness" ===> [POST /api/v1/executions/{id}/rollback-assessments]|
|   - Verifies hypothetical reversibility and evaluates prerequisites                                |
|   - Result for read-only executions: NOT_APPLICABLE (Zero mutations were performed)                |
|   - Formulates hypothetical restoration simulation (Advisory Only)                                 |
+----------------------------------------------------------------------------------------------------+
                                |
                                v
+----------------------------------------------------------------------------------------------------+
|                                    8. IMMUTABLE UNIFIED AUDIT HISTORY                              |
|                                                                                                    |
|   [Frontend /audit Page] queries [GET /api/v1/audit/events]                                        |
|   - Displays all historical approval transitions, execution runs, verifications & rollback records |
+----------------------------------------------------------------------------------------------------+
```

### 2.1 Transition Classification: Automatic vs. Explicit Actions
| Stage | Trigger Mechanism | Actor / Component |
| :--- | :--- | :--- |
| **Telemetry Generation & Alert Firing** | **Automatic** | Telemetry simulator & Prometheus Alertmanager |
| **Incident Ingestion into Database** | **Automatic** | FastAPI Webhook Handler (`POST /webhooks/alertmanager`) |
| **AI Investigation & RCA Workflow** | **Explicit Operator Click** | Operator clicks *"Run AI Investigation & RCA"* |
| **Remediation Plan Safety Validation** | **Automatic (Inside Graph)** | Deterministic Python validator node in LangGraph |
| **Approval Request Submission** | **Explicit Operator Click** | Operator clicks *"Create Approval Request"* |
| **Approval Decision (Approve/Reject/Revise)** | **Explicit Approver Click** | Distinct Authorized SRE Lead (`sre-lead-charlie`) |
| **Dry-Run Simulation Execution** | **Explicit Operator Click** | Authorized Operator (`sre-operator-dan`) in `/executions` |
| **Live Read-Only Diagnostic Execution** | **Explicit Operator Click** | Authorized Operator with explicit confirmation checkbox |
| **Post-Execution Evidence Verification** | **Explicit Operator Click** | Verifier (`can_verify`) clicks *"Run Verification"* |
| **Rollback Readiness Assessment** | **Explicit Operator Click** | Rollback Assessor clicks *"Run Assessment"* |
| **Audit Event Recording** | **Automatic (Internal)** | Backend services automatically persist append-only events |

---

## 3. Complete Frontend Page Inventory

The AegisOps frontend router (`frontend/src/app/router.tsx`) registers **11 unique routes** wrapped within the common application layout:

```
/ (Overview Dashboard)
├── /incidents (Incidents List)
│   └── /incidents/:id (Incident Detail with 7 Tab Views)
├── /investigations (Investigations & RCA Explorer)
├── /remediation (Remediation Plans Advisory Viewer)
├── /approvals (Human Approval Gateway)
├── /executions (Controlled Execution Engine)
├── /verifications (Post-Execution Evidence Verifications)
├── /rollbacks (Rollback Readiness & Restoration Planner)
├── /audit (Platform Unified Audit History)
└── /settings (System Settings & Platform Boundaries)
```

---

### Page 1: Overview Dashboard — `/`

#### A. Purpose
Provides an executive and operational bird's-eye view of real-time platform health, active incident counts by severity, pending approval backlogs, execution counts, live Prometheus service availability time-series telemetry, and recent incident logs.

#### B. Displayed Information
* **Safety Banner (Top):** Displays active controlled remediation boundaries, mandatory human approval requirement, disabled autonomous execution, and simulation-only rollback mode.
* **Metric Card: Open Incidents:** Total count of active open/investigating incidents vs total recorded incidents.
* **Metric Card: Pending Approvals:** Total count of approvals awaiting human decision vs historical total.
* **Metric Card: Completed Executions:** Total count of dry-run simulations and live diagnostics completed vs verified records.
* **Metric Card: Service Availability:** Real-time percentage (`100%`, `0%`, or `Telemetry N/A`) and Prometheus connection status (`Prometheus live` vs `Prometheus offline`).
* **Chart: Service Availability History:** Recharts area chart plotting `aegisops_sim_service_up` over the past 30 minutes with step-after interpolation.
* **Chart: Incident Severity Distribution:** Recharts donut/pie chart displaying the distribution of Critical, High, Medium, and Low incidents.
* **Table: Active & Recent Incidents:** Shows the 5 most recent incidents with columns for Title, Severity, Status, Source, Created Timestamp, and Inspect action.

#### C. Complete Interactive Control Inventory
1. **"View in Grafana" External Link:** Opens `http://localhost:3000` in a new browser tab.
2. **"View All" Incidents Button:** Navigates the operator directly to `/incidents`.
3. **Table Row Title Links:** Clicking an incident title navigates directly to `/incidents/:id`.
4. **Table Row "Inspect" Buttons:** Secondary action button navigating directly to `/incidents/:id`.

#### D. How to Use the Page
1. Review the top Metric Cards to check if any Critical incidents or Pending Approvals require immediate intervention.
2. Inspect the Service Availability History chart to determine if recent service downtime spikes have occurred.
3. Click **"Inspect"** on any high-priority incident in the recent incidents table to begin investigation.

#### E. Expected Results
* Dashboard metrics refresh automatically every 15–30 seconds via React Query.
* Clicking any incident row immediately routes to the detailed incident investigation screen.

---

### Page 2: Incident Management — `/incidents`

#### A. Purpose
Enables SREs to monitor, filter, search, inspect, and manually record production degradation events and alert streams ingested from Prometheus Alertmanager.

#### B. Displayed Information
* **Header & Incident Counter:** Shows total incident count matching active filters.
* **Search Field:** Real-time text filter querying incident title, description, or UUID.
* **Severity Filter:** Dropdown filtering incidents by `all`, `critical`, `high`, `medium`, or `low`.
* **Status Filter:** Dropdown filtering incidents by `all`, `open`, `investigating`, or `resolved`.
* **Incidents Data Table:** Columns for Severity Badge, Title & Context (including truncated UUID), Status Badge, Source (`alertmanager` or `manual`), Alert State (`firing` or `resolved` with radio antenna icon), Created Timestamp, and Action Button.
* **Empty State Component:** Rendered when no incident records match the active filter criteria.

#### C. Complete Interactive Control Inventory
1. **"Create Incident" Button:** Opens the Create Incident Modal.
2. **Search Input Field:** Live debounced text search input.
3. **Severity Filter Dropdown:** Select control with options: All Severities, Critical, High, Medium, Low.
4. **Status Filter Dropdown:** Select control with options: All Statuses, Open, Investigating, Resolved.
5. **Table Row Incident Title Link:** Navigates to `/incidents/:id`.
6. **Table Row "Inspect" Button:** Navigates to `/incidents/:id`.
7. **Create Incident Modal — Title Input:** Text input validated with Zod (min 3 chars).
8. **Create Incident Modal — Description Textarea:** Multiline text input validated with Zod (min 5 chars).
9. **Create Incident Modal — Severity Dropdown:** Select options for Critical (P1), High (P2), Medium (P3), Low (P4).
10. **Create Incident Modal — Cancel Button:** Dismisses the modal without submitting.
11. **Create Incident Modal — "Submit Incident" Button:** Calls `POST /api/v1/incidents`.

#### D. How to Use the Page
1. Type search queries or change dropdown filters to isolate active firing alerts.
2. To report an incident manually, click **"Create Incident"**, fill in the title, description, and severity, then click **"Submit Incident"**.
3. Click **"Inspect"** on any row to open the full incident view.

#### E. Expected Results
* New incidents submitted manually appear immediately at the top of the table.
* Ingested alerts from Alertmanager display with `alertmanager` source and an active `firing` pulse badge.

---

### Page 3: Incident Details — `/incidents/:id`

#### A. Purpose
The operational focal point of AegisOps. Houses complete incident context, metadata, and 7 tabbed workflow views allowing operators to trigger agentic AI investigations, inspect RCA hypotheses, review safety-validated plans, submit approval requests, and inspect downstream executions, verifications, and rollback assessments.

#### B. Displayed Information
* **Header & Breadcrumb:** Back button, Severity badge, Title, Status badge, and full UUID.
* **Action Buttons:** Top-level buttons for *"Run AI Investigation & RCA"* and *"Create Approval Request"*.
* **Tab 1: Incident Overview:** Full incident description, source badge, created timestamp, alert state, Alertmanager fingerprint, alert start timestamp, and last alert update timestamp.
* **Tab 2: AI Investigation & RCA:** Observed telemetry metric snapshot, calculated triage priority, escalation requirement, investigation observations, recommended checks, RCA summary, root-cause confirmed flag, and full hypotheses matrix with supporting/contradicting/missing evidence lists.
* **Tab 3: Remediation Plan:** Displays the latest bound advisory plan snapshot, plan version, SHA-256 hash, planning basis, and recommended action cards with validation steps and rollback considerations.
* **Tab 4: Approvals:** List of all approval versions for this incident, approval statuses, requester, timestamps, and *"Manage Decision"* button.
* **Tab 5: Executions:** List of all simulation and diagnostic runs for this incident with mode, operation ID, duration, and status.
* **Tab 6: Verifications:** List of statistical verification records, outcome badges, and duration.
* **Tab 7: Rollbacks:** List of rollback readiness evaluations with applicability, readiness status, and risk level.

#### C. Complete Interactive Control Inventory
1. **Back to Incidents Button:** Navigates to `/incidents`.
2. **"Run AI Investigation & RCA" Button:** Calls `POST /api/v1/incidents/{id}/analyze`.
3. **"Create Approval Request" Button:** Calls `POST /api/v1/incidents/{id}/approvals`.
4. **Tab Switcher Buttons (7 tabs):** Overview, Investigation, Remediation, Approvals, Executions, Verifications, Rollbacks.
5. **Investigation Tab Empty State "Run AI Investigation" Button:** Contextual button to trigger workflow.
6. **Remediation Tab "Inspect in Approvals" Button:** Routes to `/approvals`.
7. **Remediation Tab "Go to Executions Engine" Button:** Routes to `/executions`.
8. **Remediation Tab Empty State "Create Approval Request" Button:** Submits plan to approval gateway.
9. **Approvals Tab "Manage Decision" Button:** Routes to `/approvals`.
10. **Executions Tab "View Executions" Button:** Routes to `/executions`.
11. **Verifications Tab "View Verification" Button:** Routes to `/verifications`.
12. **Rollbacks Tab "Inspect Assessment" Button:** Routes to `/rollbacks`.

#### D. How to Use the Page
1. Review the Incident Overview tab to understand alert symptoms and Alertmanager metadata.
2. Click **"Run AI Investigation & RCA"**. Wait for the LangGraph agent workflow to execute.
3. Switch to the **"AI Investigation & RCA"** tab to evaluate the root cause hypotheses and metric snapshot.
4. If remediation is justified, click **"Create Approval Request"** to generate an immutable plan snapshot and submit it to the approval gateway.

---

### Page 4: Investigations & Root Cause Analysis — `/investigations`

#### A. Purpose
Provides a dedicated analytical workspace for inspecting Gemini-powered telemetry investigations, evidence verification, and multi-hypothesis root cause deduction across all recorded incidents.

#### B. Displayed Information
* **Incident Selector Dropdown:** Allows selecting any recorded incident to view its investigation findings.
* **Selected Incident Context Card:** Displays severity, title, UUID, and *"Re-Run AI Investigation"* action.
* **Deterministic Telemetry Evidence Section:** Triage priority badge (P1–P4), escalation requirement, telemetry timestamp, mandatory operator sign-off notice, and raw Prometheus metric grid.
* **Agentic Investigation Observations Card:** Investigation summary, confidence level, key observations bulleted list, and recommended diagnostic checks.
* **Root Cause Analysis (AI-Generated Hypotheses) Card:** RCA summary, most likely hypothesis card, and the full evaluated hypotheses matrix distinguishing supporting, contradicting, and missing evidence.

#### C. Complete Interactive Control Inventory
1. **Incident Selector Dropdown:** Selects target incident by title and severity.
2. **"Execute AI Investigation" / "Re-Run AI Investigation" Button:** Calls `POST /api/v1/incidents/{id}/analyze`.
3. **Empty State Action Button:** Triggers workflow when no analysis is cached.

---

### Page 5: Remediation Plans — `/remediation`

#### A. Purpose
Serves as an advisory viewer for safety-validated remediation plans generated from RCA findings. Explicitly reinforces that plans are advisory and cannot autonomously mutate production systems.

#### B. Displayed Information
* **Top Safety Banner:** Displays active read-only guards.
* **Plan Selector Dropdown:** Dropdown of all approval records (version, status, requester).
* **Plan Header Card:** Version number, truncated SHA-256 hash, status badge, requester identity, timestamp, incident summary, planning basis, and immutable safety property pills (`Human Approval Required: TRUE`, `Execution Enabled: FALSE`, `Overall Risk Level: LOW/HIGH`).
* **Recommended Actions List:** Numbered cards for each proposed action detailing action type, risk level, description, rationale, supporting evidence, validation steps, and rollback considerations.

#### C. Complete Interactive Control Inventory
1. **Plan Selector Dropdown:** Selects approval plan version.
2. **"Inspect Decision & Audit" Button:** Links directly to `/approvals`.
3. **"Execution Sandbox" Button:** Links directly to `/executions`.

---

### Page 6: Human Approval Gateway — `/approvals`

#### A. Purpose
Enforces formal human-in-the-loop authorization gating. Authorized approvers review immutable plan snapshots, verify SHA-256 hashes, and approve, reject, or request revisions on remediation requests.

#### B. Displayed Information
* **Status Filter Tabs:** Filters requests by `ALL`, `PENDING`, `APPROVED`, `REJECTED`, `REVISION REQUESTED`, `EXPIRED`, `SUPERSEDED`.
* **Approvals Data Table:** Columns for Status Badge, Version & Hash (first 16 chars), Incident ID link, Requested By, Requested At, Decision Metadata (decided by, decision reason), and Actions.
* **Decision Modal:** Displays full plan snapshot hash, planning basis, recommended actions with risk badges, formal sign-off warning, optional comment input (for approvals), mandatory reason textarea (for rejections and revisions), and the append-only decision audit trail.

#### C. Complete Interactive Control Inventory
1. **Status Filter Buttons (7 tabs):** Switches active approval status filter.
2. **Table Row Incident Link:** Routes to `/incidents/{id}`.
3. **Table Row "Approve" Button:** Opens decision modal in `approve` mode (disabled if user lacks `can_approve`).
4. **Table Row "Reject" Button:** Opens decision modal in `reject` mode (disabled if user lacks `can_approve`).
5. **Table Row "Revise" Button:** Opens decision modal in `revision` mode (disabled if user lacks `can_approve`).
6. **Table Row "Inspect" Button:** Opens decision modal in read-only inspection mode for historical records.
7. **Decision Modal — Optional Comment Input:** Text input for approval notes.
8. **Decision Modal — Mandatory Reason Textarea:** Textarea for rejection/revision explanation (min 3 chars).
9. **Decision Modal — Cancel Button:** Dismisses the modal.
10. **Decision Modal — "Confirm Decision" Button:** Submits decision via `POST /approvals/{id}/approve`, `/reject`, or `/request-revision`.

---

### Page 7: Controlled Execution Engine — `/executions`

#### A. Purpose
Provides a controlled, safe environment for executing authorized dry-run simulations or restricted read-only live diagnostics bound strictly to approved remediation plans.

#### B. Displayed Information
* **Top Safety Banner:** Displays active read-only guards.
* **Action Buttons:** Top-level buttons for *"Dry-Run Simulation"* and *"Run Live Diagnostic"*.
* **Allowlisted Operations Registry Grid:** Cards for all 5 registered operations showing operation ID, risk level, name, description, supported modes, and read-only status.
* **Execution History Table:** Columns for Mode (`simulation` or `live_diagnostic`), Status, Operation ID, Recommendation Title, Duration (ms), Operator Identity, Started Timestamp, and Inspect Details button.
* **Simulation Modal:** Approved plan selector, operation selector, recommendation index input, safety guarantee notice.
* **Live Diagnostic Modal:** Approved plan selector, operation selector, recommendation index input, read-only verification warning, and mandatory operator confirmation checkbox.
* **Execution Inspection Modal:** Execution mode, status, duration, system changes indicator (`FALSE`), raw diagnostic or simulation JSON output, and execution audit events.

#### C. Complete Interactive Control Inventory
1. **"Dry-Run Simulation" Button:** Opens the Simulation Modal (disabled if actor lacks `can_execute`).
2. **"Run Live Diagnostic" Button:** Opens the Live Diagnostic Modal (disabled if actor lacks `can_execute`).
3. **Simulation Modal — Approved Plan Select:** Selects approved plan version and hash.
4. **Simulation Modal — Operation Select:** Selects allowlisted operation.
5. **Simulation Modal — Recommendation Index Input:** Number input (1–5).
6. **Simulation Modal — Cancel Button:** Dismisses modal.
7. **Simulation Modal — "Execute Simulation" Button:** Calls `POST /api/v1/executions/simulate`.
8. **Live Diagnostic Modal — Approved Plan Select:** Selects approved plan.
9. **Live Diagnostic Modal — Diagnostic Operation Select:** Filters operations where `live_diagnostic_supported == True`.
10. **Live Diagnostic Modal — Recommendation Index Input:** Number input (1–5).
11. **Live Diagnostic Modal — Read-Only Confirmation Checkbox:** Mandatory checkbox affirming read-only scope.
12. **Live Diagnostic Modal — Cancel Button:** Dismisses modal.
13. **Live Diagnostic Modal — "Execute Diagnostic" Button:** Calls `POST /api/v1/executions/diagnose` (disabled until checkbox checked).
14. **Table Row "Inspect" Button:** Opens the Execution Inspection Modal.

---

### Page 8: Post-Execution Verifications — `/verifications`

#### A. Purpose
Performs automated statistical verification comparing pre-execution baseline metrics against post-execution observation windows to verify whether telemetry has improved, remained unchanged, or degraded.

#### B. Displayed Information
* **Verifications Data Table:** Columns for Outcome Badge (`DIAGNOSTIC_VERIFIED`, `NOT_APPLICABLE`, `INCONCLUSIVE`, `FAILED`), Execution Mode, Operation ID, Duration (ms), Verifier, Created Timestamp, and Details button.
* **Create Verification Modal:** Execution selector dropdown, Baseline Window (minutes), Follow-up Window (minutes), Minimum Samples Required input, and statistical safety policy notice.
* **Verification Detail Modal:** Truthful safeguards grid (`Remediation Success Confirmed: FALSE`, `Human Review Required: TRUE`), baseline/follow-up window criteria, query resolution step, raw metric comparison JSON, operational limitations, and verification audit events.

#### C. Complete Interactive Control Inventory
1. **"Create Verification" Button:** Opens the Create Verification Modal (disabled if actor lacks `can_verify`).
2. **Table Row "Inspect" Button:** Opens the Verification Detail Modal.
3. **Create Modal — Target Execution Select:** Dropdown selecting completed execution record.
4. **Create Modal — Baseline Window Input:** Number input (1–120 minutes, default 15).
5. **Create Modal — Follow-up Window Input:** Number input (1–120 minutes, default 15).
6. **Create Modal — Minimum Samples Input:** Number input (1–50, default 2).
7. **Create Modal — Cancel Button:** Dismisses modal.
8. **Create Modal — "Run Verification" Button:** Calls `POST /api/v1/executions/{id}/verifications`.

---

### Page 9: Rollback Readiness & Restoration Planner — `/rollbacks`

#### A. Purpose
Evaluates hypothetical reversibility, validates safety prerequisites, and formulates an advisory restoration simulation for executed operations. Explicitly enforces that rollback execution is disabled and no physical infrastructure mutations occur.

#### B. Displayed Information
* **Rollback Assessment Data Table:** Columns for Readiness Status Badge (`READY`, `NOT_APPLICABLE`, `BLOCKED`), Applicability (`not_applicable`), Risk Level Badge (`LOW`), Operation ID, Execution UUID, Assessor, Created Timestamp, and Details button.
* **Create Assessment Modal:** Target execution selector and simulation-only scope disclaimer.
* **Assessment Detail Modal:** Safety invariants display (`Rollback Execution: DISABLED`, `Human Authorization: MANDATORY TRUE`, `System Changes: ZERO MUTATION`), truthful applicability notice, prerequisite checklist (`PASS` or `INFO/BLOCKED`), simulation-only restoration planning result (target state, risk summary, simulated action list), and assessment audit trail.

#### C. Complete Interactive Control Inventory
1. **"Assess Rollback Readiness" Button:** Opens Create Assessment Modal (disabled if actor lacks `can_assess_rollback`).
2. **Table Row "Inspect" Button:** Opens Assessment Detail Modal.
3. **Create Modal — Target Execution Select:** Dropdown of completed executions.
4. **Create Modal — Cancel Button:** Dismisses modal.
5. **Create Modal — "Run Assessment" Button:** Calls `POST /api/v1/executions/{id}/rollback-assessments`.

---

### Page 10: Platform Audit History — `/audit`

#### A. Purpose
Provides a tamper-resistant, unified append-only event log capturing every approval decision, execution run, verification check, and rollback evaluation across the platform.

#### B. Displayed Information
* **Category Filter Tabs:** Filters by `ALL`, `APPROVAL`, `EXECUTION`, `VERIFICATION`, `ROLLBACK`.
* **Search Field:** Text input searching event type, actor identity, resource UUID, or incident UUID.
* **Audit Events Table:** Columns for Category Badge, Event Type, Actor, Status Transition (`previous -> new`), Resource UUID, Timestamp, and View Details action.
* **Event Details Modal:** Category, Actor, Resource ID, Incident ID, and formatted, sanitized JSON details payload.

#### C. Complete Interactive Control Inventory
1. **Category Filter Buttons (5 tabs):** Switches active audit category.
2. **Search Input Field:** Real-time text filter.
3. **Table Row "View" Button:** Opens the Event Details Modal.

---

### Page 11: System Settings & Platform Boundaries — `/settings`

#### A. Purpose
Exposes non-sensitive runtime operational configuration, connected observability endpoints, safety guardrails, and the currently authenticated operator's role permissions matrix.

#### B. Displayed Information
* **Platform Configuration Card:** Application Name, Platform Version, Environment (`DEVELOPMENT`), and Backend FastAPI Connection Status.
* **Observability Infrastructure Card:** Prometheus Telemetry URL, Prometheus health status (`Active` vs `Unreachable`), Grafana Dashboards URL with external launch link, and Prometheus proxy security scoping.
* **Remediation Guardrails Card:** Live Diagnostic Operations status (`Restricted Allowed` vs `Disabled`), Infrastructure Mutation status (`Strictly Disabled`), Autonomous Shell/SSH status (`Disabled`), and Human-in-the-Loop requirement (`Mandatory on All Plans`).
* **Operator Authorization Matrix Card:** Displays active actor identity, assigned roles, and green check / red X status for Request Approvals, Decide Approvals, Execute Diagnostics, Run Verifications, and Assess Rollback Readiness.
* **Security Architecture Notice:** Explains that secrets, database credentials, and Gemini API keys are strictly retained on the backend and never exposed to the client.

#### C. Complete Interactive Control Inventory
1. **Grafana External Link ("Open"):** Launches `http://localhost:3000` in a new browser tab.

---

## 4. Shared Frontend Components & Global Architecture

### 4.1 Global Layout (`frontend/src/components/layout/AppLayout.tsx`)
Wraps every authenticated view with the persistent left sidebar, sticky header, main content outlet, and the Persona Switcher Modal.

### 4.2 Sidebar Navigation (`Sidebar.tsx`)
* **Brand Header:** AegisOps logo, version tag (`v0.1`), and platform descriptor.
* **Primary Navigation Links:** 10 core routes with dynamic icons and active route highlighting.
* **Dynamic Notification Badges:** Shows live counts for open incidents (critical badge) and pending approvals (warning badge) sourced from `GET /overview`.
* **External Tool Integrations:** Direct link to Grafana Dashboard (`http://localhost:3000`) with live connection indicator.
* **Operator Persona Switcher Trigger:** Bottom user tile displaying active identity (`sre-operator-dan`) and assigned roles with a clickable *"Switch"* button.

### 4.3 Header Bar (`Header.tsx`)
* **Environment Indicator:** Displays `development` tag.
* **Backend API Health:** Pulse dot showing FastAPI connectivity.
* **Prometheus Connection Indicator:** Shows `Live Connected` (emerald) when Prometheus responds on port 9090, or `Local Standby` (amber) when unreachable.
* **Current Operator Pill:** Displays active identity and first two roles.
* **Global Refresh Button:** Triggers background cache invalidation and refetch across all React Query hooks.

### 4.4 Persona Switcher Modal (`PersonaSwitcherModal.tsx`)
* **Purpose:** Enables instant switching between pre-configured development personas or authenticating via custom bearer token.
* **Development Availability:** Populated via `GET /auth/actors` when `ENVIRONMENT=development`.
* **Production Boundary:** When deployed in production environments, persona switching is disabled by the backend (`GET /auth/actors` returns 403 or empty), requiring valid HTTP Bearer token headers or secure HttpOnly session cookies.

---

## 5. User Roles & Permission Matrix

The backend enforces role-based access control via typed dependency injection (`src/aegisops/core/auth.py`).

### 5.1 Role Definitions
1. **Viewer (`viewer`):** Read-only visibility across dashboards, incidents, plans, executions, verifications, and audit logs.
2. **Requester (`requester`):** Can report incidents, trigger AI investigations, and create approval requests. Cannot approve plans.
3. **Approver (`approver`):** Authorized to formally approve, reject, or request revisions on remediation plans.
4. **Operator / Executor (`operator`, `executor`):** Authorized to execute dry-run simulations and restricted read-only live diagnostics.
5. **Verifier (`verifier`):** Authorized to execute statistical post-execution verifications.
6. **Rollback Assessor (`rollback_assessor`):** Authorized to evaluate rollback readiness and generate restoration simulations.
7. **Administrator (`admin`):** Holds all permissions across all lifecycle stages.

### 5.2 Server-Side Authorization Enforcement Matrix
| Platform Capability | Viewer | Requester | Approver | Operator | Verifier | Assessor | Admin | Backend Dependency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **View Dashboard & Incidents** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | `get_current_actor` |
| **Create Manual Incident** | No | Yes | No | Yes | No | No | Yes | `get_incident_analyzer_actor` |
| **Trigger AI Investigation & RCA** | No | Yes | Yes | Yes | No | No | Yes | `get_incident_analyzer_actor` |
| **Create Approval Request** | No | Yes | No | No | No | No | Yes | `get_requester_actor` |
| **Approve Remediation Plan** | No | No | Yes* | No | No | No | Yes* | `get_approver_actor` |
| **Reject Remediation Plan** | No | No | Yes | No | No | No | Yes | `get_approver_actor` |
| **Request Plan Revision** | No | No | Yes | No | No | No | Yes | `get_approver_actor` |
| **Execute Dry-Run Simulation** | No | No | No | Yes | No | No | Yes | `get_executor_actor` |
| **Execute Live Read-Only Diagnostic**| No | No | No | Yes | No | No | Yes | `get_executor_actor` |
| **Create Post-Execution Verification**| No | No | No | Yes | Yes | No | Yes | `get_verifier_actor` |
| **Assess Rollback Readiness** | No | No | No | Yes | Yes | Yes | Yes | `get_rollback_assessor_actor` |
| **Inspect Immutable Audit History** | Yes | Yes | Yes | Yes | Yes | Yes | Yes | `get_current_actor` |

*\*Note on Separation of Duties:* When `enforce_separation_of_duties=true`, the backend strictly prevents the actor who created the approval request (`requested_by`) from approving their own plan, even if they hold the `approver` or `admin` role (`SelfApprovalError`).

---

## 6. Execution Operations Registry

All execution requests are validated against a fixed, server-side allowlist (`src/aegisops/execution/registry.py`). Unlisted or shell operations fail closed.

| Operation ID | Name | Supported Modes | Read-Only | Risk Level | Target Scope & Parameters | Expected Output |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `inspect_service_health` | Inspect Service Health | `simulation`, `live_diagnostic` | **Yes** | **Low** | Queries `aegisops_sim_service_up` (Params: `service_name`, `include_dependencies`) | Metric value, availability ratio, uptime status |
| `inspect_cpu_metrics` | Inspect CPU Metrics | `simulation`, `live_diagnostic` | **Yes** | **Low** | Queries `aegisops_sim_cpu_usage_ratio` (Params: `window_minutes`, `step`) | Sample count, latest CPU usage ratio, mean, max |
| `inspect_latency_metrics` | Inspect Latency Metrics | `simulation`, `live_diagnostic` | **Yes** | **Low** | Queries `aegisops_sim_latency_seconds` (Params: `window_minutes`, `step`) | Sample count, latest latency (seconds), trend |
| `inspect_error_rate` | Inspect Error Rate Metrics | `simulation`, `live_diagnostic` | **Yes** | **Low** | Queries `aegisops_sim_error_rate_ratio` (Params: `window_minutes`, `step`) | Sample count, latest error percentage ratio, spike detection |
| `review_service_configuration`| Review Service Configuration | `simulation` only | **Yes** | **Low** | Configuration audit of runtime flags & memory limits (Params: `component`) | Simulated configuration parameters & limits |

---

## 7. Complete Frontend-to-Backend API Mapping

| Frontend Page / Component | User Action | HTTP | Backend Endpoint | Request Purpose | Auth Required | Enforced Safety Checks |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **Header / AppLayout** | Page Load | `GET` | `/api/v1/auth/me` | Fetch active actor profile | Session / Bearer | Validates session token & roles |
| **Header / AppLayout** | Page Load / Refresh | `GET` | `/api/v1/overview` | Fetch counts & health | Session / Bearer | Read-only aggregation query |
| **Header / AppLayout** | Auto-refresh | `GET` | `/api/v1/overview/telemetry` | Fetch availability points | Session / Bearer | Clamped window (default 30m) |
| **Persona Switcher** | Open Modal | `GET` | `/api/v1/auth/actors` | List dev personas | Session / Bearer | Fails/disabled in non-dev env |
| **Persona Switcher** | Select Persona | `POST` | `/api/v1/auth/session` | Create session cookie | CSRF / Token | Validates actor against configured tokens |
| **Incidents Page** | Page Load / Filter | `GET` | `/api/v1/incidents` | List incident records | Session / Bearer | Clamped pagination (limit/offset) |
| **Incidents Page** | Submit Modal | `POST` | `/api/v1/incidents` | Create manual incident | Requester / Admin | Zod client & Pydantic backend validation |
| **Incident Details** | Page Load | `GET` | `/api/v1/incidents/{id}` | Fetch incident details | Session / Bearer | UUID validation |
| **Incident Details** | "Run AI Investigation" | `POST` | `/api/v1/incidents/{id}/analyze` | Trigger LangGraph workflow | Analyzer Role | Fails closed on missing telemetry; 120s timeout |
| **Incident Details** | "Create Approval" | `POST` | `/api/v1/incidents/{id}/approvals` | Lock plan snapshot | Requester Role | SHA-256 plan hash locking; supersedes older pending |
| **Remediation Plans** | Page Load / Select | `GET` | `/api/v1/approvals/{id}` | Inspect plan snapshot | Session / Bearer | Verifies SHA-256 integrity hash |
| **Approvals Page** | Click "Approve" | `POST` | `/api/v1/approvals/{id}/approve` | Authorize plan | Approver Role | Separation of duties (no self-approval); expiration check |
| **Approvals Page** | Click "Reject" | `POST` | `/api/v1/approvals/{id}/reject` | Reject plan | Approver Role | Mandatory reason (min 3 chars); record locked |
| **Approvals Page** | Click "Revise" | `POST` | `/api/v1/approvals/{id}/request-revision`| Request plan changes | Approver Role | Mandatory reason (min 3 chars); record locked |
| **Approvals Page** | Open Modal | `GET` | `/api/v1/approvals/{id}/events` | Fetch approval audit | Session / Bearer | Append-only event history query |
| **Executions Page** | Page Load | `GET` | `/api/v1/execution-operations` | List allowlist operations | Session / Bearer | Immutable server-side allowlist registry |
| **Executions Page** | "Execute Simulation" | `POST` | `/api/v1/executions/simulate` | Run dry-run sandbox | Executor Role | Bound to approved plan; verified idempotency key |
| **Executions Page** | "Execute Diagnostic" | `POST` | `/api/v1/executions/diagnose` | Query live Prometheus | Executor Role | Bound to approved plan; confirmation checkbox; read-only |
| **Executions Page** | Open Modal | `GET` | `/api/v1/executions/{id}/events` | Fetch execution audit | Session / Bearer | Append-only execution events |
| **Verifications Page** | "Run Verification" | `POST` | `/api/v1/executions/{id}/verifications` | Statistical comparison | Verifier Role | Requires terminal execution; epsilon tolerance |
| **Verifications Page** | Open Modal | `GET` | `/api/v1/verifications/{id}/events`| Fetch verification audit | Session / Bearer | Append-only verification events |
| **Rollbacks Page** | "Run Assessment" | `POST` | `/api/v1/executions/{id}/rollback-assessments`| Rollback readiness eval | Assessor Role | Evaluates reversibility; execution disabled |
| **Rollbacks Page** | Open Modal | `GET` | `/api/v1/rollback-assessments/{id}/events`| Fetch rollback audit | Session / Bearer | Append-only rollback events |
| **Audit History Page**| Filter / Search | `GET` | `/api/v1/audit/events` | Unified audit trail | Session / Bearer | Union query across all 4 event tables |
| **Settings Page** | Page Load | `GET` | `/api/v1/system/settings` | Non-sensitive runtime config | Session / Bearer | Secrets & API keys sanitized and excluded |

---

## 8. Status & Operational Terminology Reference

| Domain | Status / Term | Visual Indicator | Operational Meaning |
| :--- | :--- | :--- | :--- |
| **Incident Severity** | `critical` | Rose Badge | P1: Major outage, service failure, or critical degradation. |
| | `high` | Amber Badge | P2: Elevated error rates, latency breach, or service degradation. |
| | `medium` | Blue Badge | P3: Non-critical component disruption or threshold warning. |
| | `low` | Green Badge | P4: Informational alert or minor cosmetic telemetry deviation. |
| **Incident Status** | `open` | Amber Badge | Active alert recorded; no formal resolution completed. |
| | `investigating` | Blue Badge | Investigation workflow triggered or actively underway. |
| | `resolved` | Slate Badge | Incident mitigation verified; alert condition cleared. |
| **Alert State** | `firing` | Pulsing Amber Antenna | Alertmanager currently actively firing alert notifications. |
| | `resolved` | Gray Radio Icon | Alert condition has ceased in Prometheus. |
| **Approval Status** | `pending` | Amber Warning Badge | Awaiting formal human review; cannot be executed. |
| | `approved` | Emerald Success Badge | Authorized by an SRE approver; eligible for execution. |
| | `rejected` | Rose Danger Badge | Rejected by an SRE approver; permanently ineligible. |
| | `revision_requested`| Blue Medium Badge | Changes requested; requires generating a new plan version. |
| | `expired` | Slate Default Badge | Authorization window expired before decision was made. |
| | `superseded` | Slate Default Badge | Rendered obsolete by a newly submitted plan version. |
| **Execution Mode** | `simulation` | Indigo Info Badge | Synthetic dry-run sandbox execution. Zero network access. |
| | `live_diagnostic` | Amber Warning Badge | Restricted Prometheus metric telemetry query. Read-only. |
| **Execution Status** | `simulated` | Indigo Badge | Dry-run simulation completed successfully. |
| | `diagnosed` | Emerald Badge | Read-only telemetry query completed and samples recorded. |
| | `failed` | Rose Danger Badge | Execution rejected due to scope error or Prometheus timeout. |
| **Verification Outcome**| `diagnostic_verified`| Emerald Success Badge | Telemetry query verified observations aligned with plan. |
| | `not_applicable` | Slate Default Badge | Execution was a dry-run simulation; telemetry check N/A. |
| | `inconclusive` | Amber Warning Badge | Insufficient metric samples within observation window. |
| | `failed` | Rose Danger Badge | Follow-up observation indicated further degradation. |
| **Rollback Applicability**| `not_applicable` | Cyan / Default Badge | Execution was non-mutating; no physical state to revert. |
| **Rollback Readiness** | `ready` | Emerald Badge | All safety prerequisites satisfied for restoration simulation. |

---

## 9. Realistic Operator Walkthrough: High Latency Incident

Below is a step-by-step walkthrough of how an on-call SRE operates AegisOps during a production latency breach:

### Step 1: Detect Alert on Dashboard
1. Operator Dan logs into AegisOps (`http://localhost:5173`) as `sre-operator-dan`.
2. On the **Overview Dashboard**, Dan observes the *Open Incidents* metric card increment. In the *Active & Recent Incidents* table, a High Severity incident appears:
   * **Title:** `High API Latency Spike (>500ms)`
   * **Source:** `alertmanager` | **Alert State:** `firing`
3. Dan clicks **"Inspect"** to open the incident details (`/incidents/{uuid}`).

### Step 2: Review Telemetry & Trigger AI Investigation
1. On the **Incident Overview** tab, Dan reviews the Alertmanager metadata and description.
2. Dan clicks **"Run AI Investigation & RCA"**.
3. The UI indicates background execution as LangGraph runs:
   * Queries Prometheus for instantaneous metrics (`aegisops_sim_latency_seconds = 0.85s`).
   * Queries historical range data covering the 30 minutes before alert firing.
   * Prompts Gemini (`gemini-3.5-flash-lite`) to deduce root causes.
4. The UI automatically navigates to the **AI Investigation & RCA** tab. Dan reads:
   * **RCA Summary:** *"Connection contention and elevated thread utilization causing API response delay."*
   * **Hypothesis 1 (High Confidence):** *"Upstream connection pooling delay."*
   * **Supporting Evidence:** `aegisops_sim_latency_seconds = 0.85` | **Contradicting:** `None` | **Missing:** `Thread dump logs`.

### Step 3: Request Remediation Plan Approval
1. Dan clicks the **"Create Approval Request"** button.
2. The backend generates a plan version (`v1`), executes the deterministic Python safety validator, computes the SHA-256 hash (`e3b0c44298fc1c14...`), and locks the record with status `PENDING`.
3. The UI automatically transitions to the **Approvals** tab. Dan cannot approve the plan because Dan requested it (Self-approval prevention enforced).

### Step 4: Approver Reviews and Signs Off
1. SRE Lead Charlie opens the Persona Switcher and selects `sre-lead-charlie` (or Charlie logs in with their token).
2. Charlie navigates to `/approvals` and clicks **"Approve"** on version 1.
3. In the Decision Modal, Charlie reviews the plan hash, recommended actions (`inspect_latency_metrics`), inputs an optional comment: *"Authorized read-only diagnostic review"*, and clicks **"Confirm APPROVE"**.
4. The status updates immediately to `APPROVED`.

### Step 5: Execute Approved Live Diagnostic
1. Dan returns to `/executions` and clicks **"Run Live Diagnostic"**.
2. In the modal, Dan selects the approved plan (`Version 1`), chooses the allowlisted operation `inspect_latency_metrics`, selects Recommendation Index `1`, and checks the mandatory confirmation box:
   * *"I confirm that this operation is read-only and authorized by the linked approval request."*
3. Dan clicks **"Execute Diagnostic"**.
4. Within 150ms, the execution completes. Dan inspects the output:
   * Mode: `LIVE_DIAGNOSTIC` | System Changes: `FALSE` | Duration: `42 ms`
   * Prometheus telemetry result displays live latency samples and statistical summary.

### Step 6: Post-Execution Verification & Rollback Evaluation
1. Dan navigates to `/verifications` and clicks **"Create Verification"**.
2. Dan selects the execution ID, keeps baseline window at 15m and follow-up window at 15m, and clicks **"Run Verification"**.
3. Verification completes with outcome `DIAGNOSTIC_VERIFIED` and explicitly records `remediation_success_confirmed = False` (confirming that running a diagnostic does not claim to have repaired the service).
4. Dan navigates to `/rollbacks` and clicks **"Assess Rollback Readiness"**.
5. The assessment completes with readiness `READY`, applicability `NOT_APPLICABLE`, and notes that since no system mutations occurred, operational risk is zero.
6. Dan inspects `/audit` to verify that every single transition was permanently logged.

---

## 10. Frontend Functionality Status & Verification Audit

| Category | Component / Feature | Route / Location | Verification Method | Status | Notes / Observations |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Implemented & Browser-Verified** | Overview Dashboard | `/` | Browser Navigation | **PASSED** | Renders metric cards, area chart, pie chart, recent incidents table. |
| **Implemented & Browser-Verified** | Incidents List & Filtering | `/incidents` | Browser Navigation | **PASSED** | Search input, severity filter, status filter, and empty states fully functional. |
| **Implemented & Browser-Verified** | Manual Incident Creation | `/incidents` | Form & API Verification | **PASSED** | Zod-validated modal submits to `POST /incidents` and updates React Query cache. |
| **Implemented & Browser-Verified** | Incident Detail Tabs | `/incidents/:id` | Browser Navigation | **PASSED** | All 7 tabs render and display related context without errors. |
| **Implemented & Browser-Verified** | AI Investigation & RCA | `/investigations` | Browser Navigation | **PASSED** | Renders telemetry grid, observations, and hypotheses matrix. |
| **Implemented & Browser-Verified** | Remediation Advisory Viewer | `/remediation` | Browser Navigation | **PASSED** | Renders plan hash, safety badges, and action cards with validation steps. |
| **Implemented & Browser-Verified** | Human Approval Gateway | `/approvals` | Browser Navigation | **PASSED** | Renders 7 status tabs, decision modal, and audit trail. |
| **Implemented & Browser-Verified** | Controlled Executions | `/executions` | Browser Navigation | **PASSED** | Renders 5 allowlist cards, simulation modal, diagnostic modal with checkbox. |
| **Implemented & Browser-Verified** | Post-Execution Verification | `/verifications` | Browser Navigation | **PASSED** | Renders criteria modal, outcome badges, and mathematical comparison view. |
| **Implemented & Browser-Verified** | Rollback Readiness | `/rollbacks` | Browser Navigation | **PASSED** | Renders applicability card, simulation restoration view, prerequisite list. |
| **Implemented & Browser-Verified** | Unified Audit History | `/audit` | Browser Navigation | **PASSED** | Category filters, text search, and JSON details modal render properly. |
| **Implemented & Browser-Verified** | System Settings & Permissions| `/settings` | Browser Navigation | **PASSED** | Renders environment info, guardrails, and operator authorization matrix. |
| **Implemented & Browser-Verified** | Persona Switcher Modal | Global Header | Browser Interaction | **PASSED** | Lists development personas; switches session cookie and invalidates cache. |
| **Conditionally Available** | Live Diagnostics | `/executions` | Environment Flag | **CONDITIONAL** | Enabled only when `LIVE_DIAGNOSTICS_ENABLED=true` in backend `.env`. |
| **Conditionally Available** | Development Persona Switcher | Global Header | Environment Flag | **CONDITIONAL** | Available in `development`; intentionally disabled by backend in production. |
| **Missing / Incomplete** | Actual System Mutation Engine| N/A | Architecture Inspection | **BY DESIGN** | Intentionally not implemented to preserve strict zero-mutation invariants. |
| **Missing / Incomplete** | Real Rollback Execution Engine| N/A | Architecture Inspection | **BY DESIGN** | Intentionally disabled; platform supports readiness simulation only. |

---

## 11. Known Limitations & Architectural Invariants

1. **Advisory Plan Execution:** Remediation actions proposed by the AI planning agent are strictly advisory recommendations. The platform does not possess autonomous agents capable of modifying configuration files, restarting cloud servers, or modifying database tables.
2. **Read-Only Telemetry Diagnostics:** Live diagnostic execution is strictly scoped to Prometheus query endpoints. It cannot execute CLI commands, SQL queries, or remote system scripts.
3. **Simulation-Only Rollbacks:** Rollback assessments evaluate hypothetical reversibility based on allowlisted definitions. No automated rollback commands are executed against target infrastructure.
4. **Separation of Duties Policy:** In compliance-controlled environments, self-approval is blocked at the database and service layer. If an operator submits an approval request, another actor with `approver` permissions must decide it.
5. **Session & CSRF Security:** For cookie-authenticated sessions, all state-changing HTTP requests (`POST`, `PUT`, `DELETE`, `PATCH`) must supply a valid `X-CSRF-Token` header matching the HttpOnly session cookie, protecting against Cross-Site Request Forgery.
