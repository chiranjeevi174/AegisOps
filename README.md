# AegisOps | Agentic SRE & Autonomous Incident Response Platform

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/AI-LangGraph_StateGraph-blueviolet)
![Google Gemini](https://img.shields.io/badge/LLM-Gemini_2.5_Flash-8E75B2?logo=google&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Theme-Obsidian_%2B_Copper-b87333)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-v2.54-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-v11.1-F46800?logo=grafana&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker-Compose_v2-2496ED?logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Backend_Tests-245_Passing-brightgreen)
![Vitest](https://img.shields.io/badge/Frontend_Tests-15_Passing-brightgreen)

**AegisOps** is an enterprise-grade, agentic Site Reliability Engineering (SRE) and autonomous incident response platform. It bridges continuous infrastructure observability with multi-agent AI root cause analysis, deterministic safety controls, cryptographic plan integrity, and human-governed remediation execution.

The platform is built on an uncompromising architectural principle:

> **"AI investigates, correlates telemetry, and reasons over hypotheses. Deterministic safety controls and authorized humans govern execution."**

---

## Application Showcase

The AegisOps frontend is built with React 18, TypeScript, and a high-density **Obsidian + Copper** enterprise command center theme designed specifically for mission-critical operations rooms and SRE on-call teams.

### Main SRE Command Center Overview

![AegisOps Overview Dashboard](docs/images/dashboard.png)
*Figure 1: High-density operational dashboard featuring active incident metrics, severity breakdown, platform health status, real-time MTTR telemetry, and active workflow shortcuts.*

---

### Incident Response & Agentic Lifecycle Walkthrough

| Incident Management Console | Incident Lifecycle & Context |
|:---:|:---:|
| ![Incident Management](docs/images/incident-management.png) | ![Incident Details](docs/images/incident-details.png) |
| *Figure 2: Ingested Prometheus & Alertmanager alerts, multi-status filtering, automated triage tiering, and severity indicators.* | *Figure 3: Granular incident view linking alert payloads, telemetry snapshots, LangGraph investigations, and audit logs.* |

| Agentic AI Investigation & RCA | Remediation Planning & Safety Validation |
|:---:|:---:|
| ![AI Investigation](docs/images/ai-investigation.png) | ![Remediation Plan](docs/images/remediation-plan.png) |
| *Figure 4: LangGraph multi-agent output showing metric anomalies, ranked hypotheses, and supporting/contradicting/missing evidence.* | *Figure 5: Structured advisory recovery plan, blast radius estimation, deterministic safety verdict, and SHA-256 integrity hash.* |

| Human Approval Gateway | Controlled Execution & Operations Registry |
|:---:|:---:|
| ![Approval Workflow](docs/images/approval-workflow.png) | ![Execution Details](docs/images/execution-details.png) |
| *Figure 6: Role-based approval modal enforcing strict separation of duties (requester ≠ approver) and tamper-proof verification.* | *Figure 7: Execution engine modal displaying parameters, registry binding, and real-time execution results.* |

| Post-Execution Verification | Grafana Platform Observability |
|:---:|:---:|
| ![Verification Results](docs/images/verification-results.png) | ![Grafana Dashboard](docs/images/grafana-dashboard.png) |
| *Figure 8: Baseline vs follow-up window statistical comparison with transparent handling of inconclusive results.* | *Figure 9: Live Grafana dashboard tracking latency percentiles (p50/p95/p99), CPU load, and synthetic fault injection impact.* |

---

## 1. Why AegisOps?

Modern microservice architectures generate millions of telemetry signals per second. When an outage occurs, on-call engineers face severe cognitive overload, fragmented toolchains, and alert storms. Mean Time to Resolution (MTTR) stretches as engineers manually correlate metrics, sift through logs, construct hypotheses, and draft incident runbooks under high pressure.

### The Pitfalls of Naive LLM Implementations in SRE

Attempting to solve incident response with simple "LLM wrappers" or unconstrained conversational AI bots introduces severe risks:

- **Unbounded, Destructive Command Execution:** LLMs hallucinate shell commands, syntax, or arguments. Granting an LLM direct terminal access or shell execution privileges (`rm -rf`, unbound `kubectl delete`) risks catastrophic service destruction.
- **Prompt-Based Safety Illusions:** System prompts alone cannot guarantee security. Prompt injection, model drift, and edge-case ambiguity easily bypass soft instructions.
- **Plan Drift & Tampering:** When an AI suggests a remediation, there is no guarantee that the plan executed in production matches the exact advisory plan that was inspected and authorized.
- **Blurred Accountability:** In an unconstrained agent model, operational decisions lack legal and compliance auditability. When an outage worsens, there is no forensic record of who authorized the action and why.

### The AegisOps Solution

AegisOps eliminates these vulnerabilities through a multi-layered, defense-in-depth architecture:

1. **Deterministic Safety Validation:** Safety constraints are written in compiled Python code, not conversational prompts. The platform strictly forbids arbitrary shell execution, container termination, or unsanctioned cloud mutations.
2. **Cryptographic Plan Integrity:** Every remediation plan receives an immutable SHA-256 fingerprint. Any modification to a plan after human submission invalidates the approval gateway.
3. **Strict Separation of Duties:** An engineer who creates or requests approval for a remediation plan is cryptographically and logically prohibited from approving it. Approvals require independent sign-off from an authorized SRE Lead or Approver.
4. **Evidence-Grounded Reasoning:** Root-cause hypotheses are validated against three distinct evidence categories: *Supporting Evidence*, *Contradicting Evidence*, and *Missing Evidence*.
5. **Bounded Execution Architecture:** Execution is strictly categorized into three controlled modes: Safe Dry-Run Simulation, Whitelisted Read-Only Diagnostics, and Isolated Demo Remediation against a local evaluation workload. Production infrastructure remains completely isolated from mutations.
6. **Post-Execution Statistical Verification:** Actions are judged by empirical telemetry deltas comparing baseline and follow-up metric windows. If statistical confidence cannot be established, the platform truthfully reports an `inconclusive` outcome rather than hallucinating success.

---

## 2. Key Features

| Capability | Technical Description | Operational Benefit |
|---|---|---|
| **Automated Alert Ingestion** | Authenticated Alertmanager webhook receiver with payload deduplication, fingerprint hashing, and status reconciliation. | Eliminates alert duplicate storms and centralizes incident entry. |
| **Intelligent Triage** | Deterministic rule-based priority classification and blast radius calculation based on alert labels and service tier. | Categorizes severity (P1–P4) instantly without latency or hallucinations. |
| **Multi-Agent LangGraph RCA** | Orchestrated LangGraph StateGraph collecting current and historical Prometheus metrics, invoking Google Gemini for hypothesis ranking. | Evaluates anomalies with explicit supporting, contradicting, and missing evidence. |
| **Deterministic Safety Validator** | Independent Python safety engine checking blast radius, operation whitelists, prohibited commands, and risk levels. | Enforces security boundaries completely outside the LLM prompt layer. |
| **Cryptographic Plan Fingerprinting** | Canonical JSON serialization hashed via SHA-256. Bindings are validated before every lifecycle transition. | Guarantees that what was reviewed is identical to what is executed. |
| **Separation of Duties Gateway** | Versioned approval request workflow enforcing `requester != approver` and expiration timeouts. | Complies with enterprise SOC 2 / ISO 27001 operational standards. |
| **Controlled Execution Engine** | Granular execution registry supporting dry-run simulation, Prometheus read-only diagnostics, and demo remediation. | Eliminates arbitrary shell/SSH risks while providing authentic portfolio demos. |
| **Post-Execution Verification** | Multi-window statistical comparison of Prometheus metrics (CPU, latency, error rates) post-remediation. | Validates true service recovery and reports inconclusive states transparently. |
| **Rollback Readiness Engine** | Automated assessment of restoration prerequisites, blast radius, and demo state rollback against the evaluation workload. | Verifies reversibility before actions are applied and restores test states. |
| **Immutable Audit Logging** | Append-only PostgreSQL audit trail capturing every alert, investigation, approval decision, execution event, and verification. | Provides a forensic timeline for post-mortems and compliance reviews. |
| **Obsidian + Copper UI** | React 18, TypeScript, Tailwind CSS, TanStack Query, and Recharts optimized for high-density NOC operations. | High readability, instant state reactivity, and rich inspection modals. |
| **Full Observability Stack** | Native integration with Prometheus v2.54, Alertmanager v0.27, and Grafana v11.1 dashboards. | Real-time service monitoring, metric scraping, and alert routing. |

---

## 3. System Architecture

AegisOps strictly decouples observability, agentic reasoning, safety enforcement, and execution into distinct operational boundaries:

```mermaid
flowchart TD
    subgraph OBSERVABILITY["Observability & Monitored Infrastructure"]
        TS["Telemetry Simulator / Workload<br/>(Port 8001)"] -->|Scrape Metrics| PROM["Prometheus Server<br/>(Port 9090)"]
        PROM -->|Evaluate Alert Rules| AM["Alertmanager<br/>(Port 9093)"]
        PROM -->|Visualize Metrics| GRAF["Grafana SRE Dashboards<br/>(Port 3000)"]
    end

    subgraph INGESTION["Ingestion & Persistence"]
        AM -->|Authenticated Webhook| API_INGEST["FastAPI Webhook Receiver<br/>(Deduplication & Fingerprinting)"]
        API_INGEST --> DB[(PostgreSQL 17 Database<br/>Port 5433)]
    end

    subgraph AGENTIC["LangGraph Multi-Agent Investigation Engine"]
        UI_OP["SRE Operator"] -->|Initiate Analysis| LG_START["Investigation Trigger"]
        LG_START --> N1["Triage Node<br/>(Priority & Blast Radius)"]
        N1 --> N2["Current Evidence Node<br/>(Prometheus Snapshots)"]
        N2 --> N3["Historical Evidence Node<br/>(Baseline Telemetry Window)"]
        N3 --> N4["Investigation & RCA Node<br/>(Gemini 2.5 Flash Reasoning)"]
        N4 --> N5["Remediation Planning Node<br/>(Advisory Recovery Actions)"]
        N5 --> N6["Deterministic Safety Validator<br/>(Compiled Python Rule Engine)"]
        N6 --> PLAN["Safety-Validated Remediation Plan<br/>+ SHA-256 Fingerprint"]
    end

    subgraph GOVERNANCE["Human Approval Gateway (Separation of Duties)"]
        PLAN -->|Submit Request| REQ["Approval Request<br/>(Requester: Alice)"]
        REQ --> GATE{"Approval Decision Gate<br/>(Requester ≠ Approver)"}
        GATE -->|Self-Approval Attempt| REJECT_BLOCK["HTTP 403 Forbidden<br/>(Separation of Duties Violation)"]
        GATE -->|Rejected / Expired| REJECTED["Execution Blocked"]
        GATE -->|Approved by Lead Charlie| APPROVED["Approved Execution Snapshot<br/>(SHA-256 Verified)"]
    end

    subgraph EXECUTION["Controlled Execution & Rollback Engine"]
        APPROVED --> DISPATCH{"Execution Mode Dispatcher<br/>(Operator: Dan)"}
        DISPATCH -->|Mode: Simulation| SIM["Dry-Run Simulator<br/>(Synthetic Audit Payload)"]
        DISPATCH -->|Mode: Diagnostic| DIAG["Whitelisted Read-Only Diagnostics<br/>(PromQL Queries)"]
        DISPATCH -->|Mode: Demo Remediation| DEMO_EXEC["Isolated Demo Workload Mutation<br/>(Mutates Simulator on Port 8001)"]

        SIM --> VERIF["Post-Execution Verification<br/>(Statistical Window Comparison)"]
        DIAG --> VERIF
        DEMO_EXEC --> VERIF

        VERIF --> ROLLBACK{"Rollback Assessment"}
        ROLLBACK -->|Demo Rollback Triggered| DEMO_RB["Demo State Restoration<br/>(Restores Port 8001 Degraded State)"]
    end

    subgraph AUDIT["Enterprise Audit Trail"]
        API_INGEST -.-> AUDIT_LOG[(Immutable Audit History)]
        GATE -.-> AUDIT_LOG
        DISPATCH -.-> AUDIT_LOG
        VERIF -.-> AUDIT_LOG
        ROLLBACK -.-> AUDIT_LOG
    end

    DB --- AUDIT_LOG
```

---

## 4. End-to-End Incident Lifecycle

AegisOps orchestrates incidents through 9 structured, auditable phases:

```
[1. Alert Ingestion] ➔ [2. Triage] ➔ [3. AI Investigation] ➔ [4. Plan & SHA-256] ➔ [5. Human Approval] ➔ [6. Controlled Execution] ➔ [7. Verification] ➔ [8. Rollback Assessment] ➔ [9. Audit Trail]
```

1. **Alert Ingestion & Deduplication:** Alertmanager fires an authenticated webhook to FastAPI (`/api/v1/incidents/webhook`). AegisOps deduplicates active alerts by fingerprint, updating the existing record or creating a new incident in PostgreSQL.
2. **Intelligent Triage:** Deterministic rule evaluation assigns incident priority (`P1` to `P4`) based on the affected service tier, alert severity, and impact scope.
3. **Multi-Agent LangGraph Investigation:** An authorized operator clicks **"Execute AI Investigation"**. LangGraph triggers a 7-stage state machine collecting metric anomalies, gathering historical baselines, and querying Gemini 2.5 Flash for root-cause hypotheses with explicit supporting/contradicting/missing telemetry.
4. **Remediation Plan Generation & SHA-256 Hashing:** LangGraph drafts advisory remediation actions. The plan is passed through the deterministic safety validator to ensure no prohibited commands or excessive blast radii exist. The plan is saved with an immutable SHA-256 canonical hash.
5. **Human Approval Gateway (Separation of Duties):** An engineer (`sre-engineer-alice`) submits the plan for approval. An independent SRE lead (`sre-lead-charlie`) reviews the blast radius, safety checks, and SHA-256 hash before approving. Alice cannot approve her own request.
6. **Controlled Execution:** An operator (`sre-operator-dan`) executes the approved plan. Depending on the action type and environment configuration, AegisOps runs a dry-run simulation, a whitelisted read-only Prometheus diagnostic, or an isolated demo remediation against the local simulator.
7. **Post-Execution Verification:** The verification engine samples Prometheus metrics over pre- and post-execution observation windows, calculating statistical deltas for CPU utilization, request latency, and error rates.
8. **Rollback Readiness & Restoration:** The rollback engine evaluates restoration feasibility, blast radius, and prerequisites. In the demo sandbox, operators can execute a demo rollback to restore the simulator to its pre-incident degraded state for continuous testing.
9. **Unified Audit Logging:** Every transition, decision, authorization token, execution output, and verification result is committed to the append-only audit trail in PostgreSQL.

---

## 5. Agentic AI & LangGraph Architecture

AegisOps avoids naive single-prompt LLM patterns by modeling incident analysis as a state machine using **LangGraph**.

### LangGraph StateGraph Architecture

The investigation graph is defined with a typed state schema (`IncidentState`):

```python
# Simplified LangGraph Workflow Architecture
builder = StateGraph(IncidentState)

builder.add_node("triage", triage_node)
builder.add_node("current_evidence", current_evidence_node)
builder.add_node("historical_evidence", historical_evidence_node)
builder.add_node("investigation", investigation_node)
builder.add_node("rca", rca_node)
builder.add_node("remediation_planning", remediation_planning_node)
builder.add_node("safety_validation", safety_validation_node)

builder.set_entry_point("triage")
builder.add_edge("triage", "current_evidence")
builder.add_edge("current_evidence", "historical_evidence")
builder.add_edge("historical_evidence", "investigation")
builder.add_edge("investigation", "rca")
builder.add_edge("rca", "remediation_planning")
builder.add_edge("remediation_planning", "safety_validation")
builder.add_edge("safety_validation", END)
```

### Specialized Graph Nodes

- **`triage_node`:** Extracts alert labels, computes blast radius, and evaluates priority tiering using deterministic rules.
- **`current_evidence_node`:** Queries Prometheus directly via PromQL for active metric anomalies (`cpu_usage_percent`, `request_latency_seconds`, `error_rate_percent`).
- **`historical_evidence_node`:** Fetches a baseline metric window (10–60 minutes prior) to establish normal operating thresholds.
- **`investigation_node`:** Prompts Google Gemini with structured telemetry, guiding the LLM to identify anomalies without speculating.
- **`rca_node`:** Synthesizes findings into ranked hypotheses with confidence scores, categorizing telemetry into **Supporting**, **Contradicting**, and **Missing** evidence.
- **`remediation_planning_node`:** Generates advisory mitigation actions, estimated recovery times, and prerequisite checks.
- **`safety_validation_node`:** Applies a deterministic Python validation engine to inspect the generated recommendations.

### Evidence Grounding & The Tri-State Evidence Model

AegisOps enforces evidence grounding by forcing the AI to categorize observed data into three explicit categories:

1. **Supporting Evidence:** Empirical observations consistent with a proposed hypothesis (e.g., CPU pegged at 94% with thread exhaustion logs).
2. **Contradicting Evidence:** Observations that weaken a hypothesis (e.g., database connection pool utilization is healthy at 12%, contradicting a database bottleneck hypothesis).
3. **Missing Evidence:** Crucial data points needed before reaching a definitive conclusion (e.g., heap memory dump or upstream gateway access logs).

### Deterministic Safety Validation (Python vs. Prompt)

In AegisOps, **the LLM is never trusted to validate its own safety**. Safety constraints are enforced by a standalone Python validator (`src/aegisops/agents/safety.py`):

```python
# Deterministic checks executed outside the LLM context
class DeterministicSafetyValidator:
    PROHIBITED_COMMAND_PATTERNS = [
        r"rm\s+-rf", r"mkfs", r"dd\s+if=", r"chmod\s+-R\s+777",
        r"drop\s+database", r"truncate", r">/dev/sd", r"kill\s+-9\s+1"
    ]

    def validate_plan(self, plan: RemediationPlan) -> SafetyVerdict:
        # Enforces blast radius thresholds
        # Enforces mandatory human approval requirement
        # Enforces allowlisted operation bindings
        # Enforces prohibition of raw shell execution
```

---

## 6. Human Approval Gateway & Separation of Duties

AegisOps embeds strict governance controls to prevent unauthorized or unintended production changes.

### Cryptographic Plan Integrity (SHA-256)

When an authorized engineer submits a remediation plan for approval:
1. The plan's action steps, target services, commands, and risk ratings are normalized into canonical JSON.
2. A SHA-256 cryptographic digest is generated and stored on the approval record:
   $$\text{Plan Hash} = \text{SHA-256}(\text{Canonicalize}(\text{RemediationPlan}))$$
3. Before any execution step is dispatched, the engine recomputes the plan hash and asserts an exact match against the approved record. Any tampering or drift immediately halts execution with an integrity violation.

### Separation of Duties Enforcement

To comply with enterprise compliance standards (SOC 2 Type II, ISO 27001), AegisOps enforces logical and cryptographic separation between operators requesting changes and leads approving them:

$$\text{Requester Identity} \neq \text{Approver Identity}$$

If a user attempts to approve an approval request they created, the backend returns an immediate **HTTP 403 Forbidden** with error code `SEPARATION_OF_DUTIES_VIOLATION`.

### SRE Persona & Role-Based Access Control Matrix

| Predefined Persona | Role | Token Header | Approval Request | Approve / Reject | Execute Actions | Assess Rollbacks | Admin Config |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| **Alice** (`sre-engineer-alice`) | Incident Responder / Requester | `aegisops-dev-requester-token` | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Charlie** (`sre-lead-charlie`) | SRE Lead / Approver | `aegisops-dev-approver-token` | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Dan** (`sre-operator-dan`) | SRE Operations Specialist | `aegisops-dev-operator-token` | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Bob** (`sre-admin-bob`) | Lead Administrator | `aegisops-dev-admin-token` | ✅ | ✅ | ✅ | ✅ | ✅ |

*Note: In local development, the UI includes a Persona Switcher modal that generates valid backend session cookies and CSRF tokens.*

---

## 7. Controlled Execution & Rollback Engine

AegisOps maintains complete transparency about its execution capabilities and operational boundaries.

### Transparent Execution Modes

```
                   ┌─────────────────────────────────────────┐
                   │        Approved Remediation Plan        │
                   └────────────────────┬────────────────────┘
                                        │
                    Dispatch Execution by Mode & Environment
                                        │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
┌──────────────────┐          ┌───────────────────┐          ┌───────────────────┐
│     Mode 1:      │          │      Mode 2:      │          │      Mode 3:      │
│     Dry-Run      │          │  Live Diagnostic  │          │  Demo Execution   │
│    Simulation    │          │  (Read-Only)      │          │ (Isolated Workload)│
├──────────────────┤          ├───────────────────┤          ├───────────────────┤
│ Synthetic audit  │          │ Whitelisted       │          │ HTTP mutation to  │
│ payload for dry- │          │ PromQL queries    │          │ evaluation target │
│ run validation.  │          │ (e.g. up, rate).  │          │ (Port 8001 only). │
│ Zero side effects│          │ Zero mutations.   │          │ Live demo impact. │
└──────────────────┘          └───────────────────┘          └───────────────────┘
```

1. **Dry-Run Simulation:** Generates a synthetic execution result and audit event. Used for testing workflows and verifying approval lifecycles without any network or host calls.
2. **Restricted Read-Only Diagnostics:** Executes allowlisted, read-only Prometheus queries (e.g., metric scraping, process status inspection). Strictly forbids write or mutation queries.
3. **Isolated Demo Execution:** In local development/demo environments, AegisOps can execute bounded operational changes against the local telemetry simulator (`http://127.0.0.1:8001`). Supported operations include:
   - `remediate_service_degradation`: Resets simulated latency, CPU, and error rate to normal operating levels.
   - `scale_demo_workload`: Dynamically adjusts simulated concurrency and worker threads.
   - `restart_demo_service`: Triggers a graceful simulated process recycling.
4. **Production Protection Boundary:** AegisOps explicitly **does not provide arbitrary SSH, bash, powershell, or unconfined cloud mutations**. It cannot modify production cloud infrastructure, patch Kubernetes deployments, or terminate production nodes.

### Rollback Engine & Demo State Restoration

The rollback architecture follows a 3-tier safety design:

1. **Rollback Readiness Assessment:** Before executing or reverting changes, the engine assesses restoration applicability, blast radius, target service availability, and prerequisite conditions.
2. **Simulated Rollback:** Evaluates hypothetical rollback steps without altering any state.
3. **Demo Rollback Execution:** In the local evaluation sandbox, operators can execute a demo rollback against `http://127.0.0.1:8001`. The engine calls the simulator's rollback endpoint, restoring the simulated workload to its prior degraded scenario (e.g., restoring CPU load to 94%) to enable repeatable demonstrations.

> [!IMPORTANT]
> **Operational Boundary Clarification:** Demo rollback exclusively restores the previous synthetic scenario on the local evaluation simulator (`http://127.0.0.1:8001`). It does **not** perform automated rollbacks against production infrastructure, live cloud clusters, or active container orchestrators. Production rollback readiness remains strictly an advisory assessment.

---

## 8. Post-Execution Verification

AegisOps evaluates remediation success through empirical metric verification rather than self-reported completion status.

### Statistical Window Sampling

Following an execution, the verification engine samples Prometheus metrics over two comparative observation windows:
- **Baseline Window ($W_0$):** Telemetry captured immediately prior to remediation.
- **Follow-Up Window ($W_1$):** Telemetry captured across the observation period following execution.

The engine computes mean, peak, and standard deviation deltas for:
- CPU Utilization (`%`)
- Request Latency ($p50$, $p95$, $p99$ in milliseconds)
- Service Error Rate (`%`)

### Truthful Outcome Reporting (Handling Inconclusive Verifications)

Many operational platforms falsely report "Success" simply because a script exited with status code `0`. AegisOps enforces statistical honesty:

| Verification Verdict | Condition | Operational Meaning |
|---|---|---|
| `remediated` | Follow-up metrics demonstrate a statistically significant reduction in CPU, latency, and error rate below alerting thresholds. | Incident can be safely resolved. |
| `degraded` | Follow-up metrics worsened or remained severely elevated following execution. | Immediate rollback or secondary intervention required. |
| `inconclusive` | Follow-up window was too brief, metric variance was excessive, or telemetry did not exhibit a statistically significant change. | Manual SRE inspection required before closing the incident. |

---

## 9. Technology Stack

| Layer | Component | Version | Technology | Purpose |
|---|---|---|---|---|
| **Backend** | API Framework | 0.115+ | Python 3.12, FastAPI, Pydantic v2 | High-performance async REST API, OpenAPI docs, webhook ingestion |
| **Agentic AI** | Orchestration | Latest | LangGraph, LangChain Core | Multi-agent state machine, evidence gathering, sequential RCA |
| **LLM** | Reasoning Model | 2.5 Flash | Google Gemini API (`gemini-2.5-flash`) | Anomaly interpretation, hypothesis ranking, advisory plan drafting |
| **Database** | Primary Store | 17.0 | PostgreSQL, SQLAlchemy 2.0 (Async), asyncpg | Acid storage for incidents, plans, approvals, executions, audit logs |
| **Migrations** | Schema Versioning | Latest | Alembic | Version-controlled database schema migrations |
| **Monitoring** | Metrics Engine | v2.54 | Prometheus | Real-time metric scraping, time-series storage, alert evaluation |
| **Alerting** | Alert Router | v0.27 | Alertmanager | Alert routing, grouping, deduplication, webhook dispatch |
| **Dashboards** | SRE Visualization | v11.1 | Grafana | Pre-configured SRE platform overview and telemetry dashboards |
| **Simulator** | Workload Fixture | Internal | Python, FastAPI, Prometheus Client | Synthetic fault injection (high CPU, latency spikes, error bursts) |
| **Frontend** | UI Framework | 18.3 | React 18, TypeScript 5.6, Vite 6 | High-density SRE NOC command center |
| **Styling** | Theme System | 3.4 | Tailwind CSS (Obsidian + Copper) | Dark enterprise palette (#100F0D, #211D19, #D97706, #059669) |
| **State / Forms**| Client State | Latest | TanStack React Query v5, React Hook Form, Zod | Async server-state caching, form validation, type-safe schemas |
| **Testing** | Backend Suite | Latest | Pytest, Pytest-Asyncio, Ruff, Pyright | 245 passing backend tests, strict linting, zero type errors |
| **Testing** | Frontend Suite | Latest | Vitest, React Testing Library, ESLint | 15 passing frontend component and integration tests |

---

## 10. Repository Structure

```
AegisOps/
├── .env.example                       # Application environment template
├── .gitignore                         # Comprehensive git ignore rules
├── alembic.ini                        # Alembic database migration configuration
├── pyproject.toml                     # Python package dependencies & tool settings
├── README.md                          # Enterprise documentation and architecture guide
│
├── docs/                              # Technical guides and system documentation
│   ├── images/                        # High-resolution genuine UI screenshots
│   │   ├── dashboard.png              # SRE Overview Command Center
│   │   ├── incident-management.png    # Ingested incidents table & filtering
│   │   ├── incident-details.png       # Incident metadata & operational context
│   │   ├── ai-investigation.png       # Multi-agent LangGraph RCA & evidence
│   │   ├── remediation-plan.png       # Safety-validated plan & SHA-256 hash
│   │   ├── approval-workflow.png      # Separation of duties approval gateway
│   │   ├── execution-details.png      # Execution engine & registry modal
│   │   ├── verification-results.png   # Statistical verification comparison
│   │   └── grafana-dashboard.png      # Grafana live observability dashboard
│   ├── architecture.md                # System design & component interaction
│   ├── api_and_database_reference.md  # REST endpoints & PostgreSQL schema specs
│   ├── development_workflow.md        # Local development setup and commands
│   ├── evaluation.md                  # Verification benchmarks & evaluation suite
│   ├── security.md                    # Safety boundaries, RBAC & fail-closed logic
│   └── windows_cmd_execution_handbook.md # Step-by-step Windows CMD operator guide
│
├── frontend/                          # React 18 + TypeScript + Vite frontend
│   ├── src/
│   │   ├── app/                       # React Router configuration & entry
│   │   ├── components/                # Reusable UI widgets & layout elements
│   │   ├── features/                  # Domain pages (incidents, approvals, etc.)
│   │   ├── services/                  # API client & session management
│   │   └── styles/                    # Obsidian + Copper Tailwind design tokens
│   ├── package.json                   # Frontend npm dependencies
│   └── vite.config.ts                 # Vite bundler configuration & proxy
│
├── infrastructure/                    # Observability & container definitions
│   ├── compose.yaml                   # Core infrastructure Docker Compose (Postgres, Prometheus, Alertmanager, Grafana)
│   ├── alertmanager/                  # Alert routing rules & webhook templates
│   ├── grafana/                       # Dashboards & datasource provisioning
│   ├── prometheus/                    # Metric scrape jobs & alerting rules
│   └── deployment/                    # Production-like isolated Docker Compose stack
│
├── migrations/                        # Alembic asynchronous schema revisions
│   └── versions/                      # Migration scripts (incidents, approvals, executions, audit)
│
├── scripts/                           # Operational utilities and test runners
│   ├── dev.py                         # Unified development lifecycle manager
│   ├── simulate_service.py            # Synthetic telemetry and fault injection simulator
│   ├── verify_demo_execution_e2e.py   # 14-stage end-to-end automated validation runner
│   ├── verify_persona_switching.py    # RBAC and separation-of-duties verification
│   ├── capture_all_screenshots.py     # Automated Playwright desktop screenshot capture
│   └── evaluate_platform.py           # Multi-suite evaluation framework runner
│
├── src/aegisops/                      # Core backend application source
│   ├── agents/                        # LangGraph workflow, nodes, and safety engine
│   ├── api/                           # FastAPI routers and Pydantic schemas
│   ├── core/                          # Configuration, database session, security utils
│   ├── domain/                        # Domain models and business logic
│   ├── execution/                     # Diagnostics runner and execution registry
│   ├── integrations/                  # Gemini, Prometheus, and Alertmanager clients
│   ├── rollback/                      # Rollback eligibility and state restoration
│   └── services/                      # Service layer (incidents, approvals, verifications)
│
└── tests/                             # Comprehensive backend automated test suite
    ├── unit/                          # Unit tests for agents, safety, and hashing
    └── integration/                   # Integration tests for APIs and database
```

---

## 11. Quickstart & Windows CMD Execution Handbook

Follow these instructions to configure, run, and demonstrate AegisOps in a Windows CMD environment.

### Prerequisites

Ensure the following tools are installed and accessible in your Windows CMD path:
1. **Python 3.12:** `python --version`
2. **uv (Fast Python Package Manager):** `uv --version` (Install via `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`)
3. **Node.js 20+ & npm:** `node --version` and `npm --version`
4. **Docker Desktop:** Ensure Docker Desktop is running with Compose v2 support (`docker compose version`)
5. **Git:** `git --version`

---

### Step 1 — Clone the Repository

```cmd
git clone https://github.com/<YOUR_ORGANIZATION_OR_USERNAME>/AegisOps.git
cd AegisOps
```

---

### Step 2 — Configure Environment Variables

Create the local application and infrastructure environment files from their templates:

```cmd
copy .env.example .env
copy infrastructure\.env.example infrastructure\.env
```

Open `.env` in Notepad to add your Google Gemini API key:

```cmd
notepad .env
```

Set the following primary variables:
```ini
ENVIRONMENT=development
AEGISOPS_DATABASE_URL=postgresql+asyncpg://aegisops_user:aegisops_dev_password@127.0.0.1:5433/aegisops
GEMINI_API_KEY=your_actual_google_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
ENABLE_DEMO_EXECUTION=true
ENABLE_DEV_PERSONA_SWITCHING=true
```

---

### Step 3 — Install Dependencies

Install Python backend dependencies using `uv`:

```cmd
uv sync --python 3.12
```

Install frontend React dependencies using `npm`:

```cmd
cd frontend
npm ci
cd ..
```

---

### Step 4 — Launch Local Infrastructure & Services

You can start the entire platform using the unified development lifecycle manager:

```cmd
:: 1. Validate environment configuration and prerequisites
uv run python scripts/dev.py check

:: 2. Launch Docker containers, database migrations, backend, simulator, and frontend
uv run python scripts/dev.py start

:: 3. Inspect live operational status
uv run python scripts/dev.py status
```

#### Alternative: Manual Launch Across Dedicated Terminals

For complete visibility into real-time server logs during demonstrations, open 4 separate Windows CMD terminals:

**Terminal 1 — Docker Infrastructure (Postgres, Prometheus, Alertmanager, Grafana):**
```cmd
docker compose -f infrastructure/compose.yaml up -d
uv run alembic upgrade head
```

**Terminal 2 — Telemetry Simulator & Fault Injector:**
```cmd
uv run python scripts/simulate_service.py
```

**Terminal 3 — FastAPI Backend Engine:**
```cmd
set PYTHONPATH=src
uv run uvicorn aegisops.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 4 — React Obsidian + Copper Frontend:**
```cmd
cd frontend
npm run dev
```

---

### Step 5 — Access Local Platform Services

| Service | Local Address | Authentication / Credentials | Description |
|---|---|---|---|
| **AegisOps Frontend** | [http://localhost:5173](http://localhost:5173) | Built-in SRE Persona Switcher | Mission-control SRE command center |
| **FastAPI Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Bearer Token / Session Cookie | Interactive OpenAPI endpoints & testing |
| **Telemetry Simulator** | [http://localhost:8001](http://localhost:8001) | None | Service metrics & fault injection endpoints |
| **Prometheus Server** | [http://localhost:9090](http://localhost:9090) | None | PromQL query console & target status |
| **Alertmanager** | [http://localhost:9093](http://localhost:9093) | Webhook bearer token | Alert notification rules & active alerts |
| **Grafana Dashboards** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` (or configured password in `.env`) | Platform Overview & service telemetry |

---

### Step 6 — SRE Persona Switching in Development

To test and demonstrate role-based workflows and separation of duties in the UI:
1. Open [http://localhost:5173](http://localhost:5173).
2. Click the **Operator Persona** badge in the top-right header.
3. Switch between identities:
   - **Alice (`sre-engineer-alice`):** Request remediation plan approval.
   - **Charlie (`sre-lead-charlie`):** Review and approve pending requests.
   - **Dan (`sre-operator-dan`):** Execute approved plans and trigger verifications.
   - **Bob (`sre-admin-bob`):** Comprehensive system administration.

---

### Step 7 — Run the Automated End-to-End Verification Runner

To verify the complete 14-stage lifecycle (incident ingestion, AI analysis, plan hashing, separation-of-duties enforcement, demo execution, verification, and demo rollback) via an automated script:

```cmd
uv run python scripts/verify_demo_execution_e2e.py
```

Expected output:
```text
[Stage 1/14] Setting simulated service degradation... OK
[Stage 2/14] Ingesting incident alert via Alertmanager webhook... OK
[Stage 3/14] Running LangGraph AI investigation & RCA... OK
[Stage 4/14] Fetching generated remediation plan... OK
[Stage 5/14] Creating approval request as sre-engineer-alice... OK
[Stage 6/14] Verifying separation of duties (Alice self-approval blocked)... OK (HTTP 403)
[Stage 7/14] Approving plan as sre-lead-charlie... OK (HTTP 200)
[Stage 8/14] Executing demo remediation as sre-operator-dan... OK
[Stage 9/14] Verifying simulator telemetry restored to healthy... OK (CPU 25%, Latency 80ms)
[Stage 10/14] Executing post-execution verification... OK (Outcome: inconclusive - statistical honesty enforced)
[Stage 11/14] Assessing rollback readiness... OK (Readiness: ready_for_review, Applicability: applicable)
[Stage 12/14] Executing demo rollback... OK (Restores simulated scenario to high_cpu)
[Stage 13/14] Verifying simulator restored to pre-incident degraded state... OK (CPU restored to 94%)
[Stage 14/14] Validating audit history trail... OK
All 14 lifecycle stages passed successfully!
```

> [!NOTE]
> **Truthful Verification & Rollback Disclosures:**
> - **Inconclusive Verification Outcome (Stage 10):** While Stage 9 confirms that demo remediation successfully restored healthy telemetry on the simulator, the Stage 10 post-execution verification against Prometheus is truthfully reported as `inconclusive`. This occurs because the automated test runs immediately (~2 seconds post-execution), which is too brief to satisfy the minimum statistical sampling window required for automated sign-off. The platform refuses to falsely claim remediation success without statistical certainty.
> - **Demo Rollback Scope (Stages 12–13):** Demo rollback exclusively reverts the local telemetry simulator (`http://127.0.0.1:8001`) from `healthy` back to its prior degraded scenario (`high_cpu`, CPU 94%). It does **not** perform mutations against production infrastructure, live cloud clusters, or Kubernetes nodes.

---

## 12. Production-Like Docker Deployment

AegisOps includes an isolated, single-server production-like deployment configuration (`infrastructure/deployment/compose.yaml`).

> **Scope Note:** This configuration demonstrates single-node containerized deployment with an Nginx reverse proxy, non-root application users, internal network isolation, and automated database migrations. It is designed for controlled staging and portfolio verification, not as an unconstrained public-cloud production cluster.

### Deploying the Production-Like Stack

```cmd
:: 1. Prepare deployment environment file
copy infrastructure\deployment\.env.example infrastructure\deployment\.env

:: 2. Build and launch isolated deployment containers
docker compose --env-file infrastructure/deployment/.env -p aegisops-prod -f infrastructure/deployment/compose.yaml up -d --build

:: 3. Run deployment health verification script
uv run python scripts/verify_deployment.py
```

### Production-Like Port Mapping

| Service | Staging URL | Network Exposure |
|---|---|---|
| **Nginx Web & Proxy** | [http://localhost:8080](http://localhost:8080) | Public host binding |
| **FastAPI Backend** | Internal container network | Internal only (proxied by Nginx) |
| **PostgreSQL Database**| Internal container network | Internal only (no host publishing) |
| **Prometheus** | [http://localhost:9091](http://localhost:9091) | Public host binding |
| **Grafana** | [http://localhost:3001](http://localhost:3001) | Public host binding |
| **Alertmanager** | [http://localhost:9094](http://localhost:9094) | Public host binding |

---

## 13. Testing, Linting & Verification Suite

AegisOps maintains high engineering standards with comprehensive automated test suites and strict static analysis:

### Backend Test Suite & Linters

```cmd
:: Run ruff linter
uv run ruff check src tests scripts migrations evaluation

:: Run ruff formatting validation
uv run ruff format --check src tests scripts migrations evaluation

:: Run complete backend pytest suite
uv run pytest -q

:: Run static type checking via pyright
npx pyright src evaluation
```

### Frontend Test Suite & Linters

```cmd
cd frontend

:: Run ESLint
npm run lint

:: Run TypeScript type checking
npm run typecheck

:: Run Vitest component and integration tests
npm run test -- --run

:: Test production bundle build
npm run build
cd ..
```

### Platform Evaluation Suite (Deterministic & Mocked)

```cmd
uv run python scripts/evaluate_platform.py --suite all --mode mocked
```

### Validated Test Metrics

| Test Suite | Metric / Scope | Status | Result |
|---|---|---|---|
| **Backend Regression (Pytest)** | Unit, API, LangGraph, Safety, RBAC | Passed | **245 passed** (100%) |
| **Frontend Tests (Vitest)** | Navigation, Incidents, Approvals, Executions | Passed | **15 passed** (100%) |
| **Ruff Linter** | PEP 8, flake8, bandit, import sorting | Passed | **0 errors** |
| **Ruff Formatter** | Code style & formatting | Passed | **156 files compliant** |
| **Pyright Type Checker** | Type safety on `src` and `evaluation` | Passed | **0 errors, 0 warnings** |
| **Vite Production Build** | TypeScript compilation & bundling | Passed | **Built clean in 5.96s** |
| **E2E Lifecycle Runner** | 14-stage end-to-end integration flow | Passed | **14/14 stages passed** |

---

## 14. Security, Governance & Fail-Closed Boundaries

AegisOps is engineered to **fail closed**. If authorization fails, plan integrity checks fail, or required parameters are absent, execution is rejected immediately.

1. **Role-Based Authorization:** Every mutating endpoint asserts the caller's role (`requester`, `approver`, `operator`, `admin`). Unauthenticated requests return HTTP 401; unauthorized operations return HTTP 403.
2. **Session Security & CSRF:** Browser interactions use `HttpOnly`, `SameSite=Lax` session cookies paired with cryptographic CSRF token headers (`X-CSRF-Token`).
3. **Plan Immutability:** Remediation plans cannot be altered once approved. Any state change outside the approved record invalidates the SHA-256 fingerprint.
4. **Secret Redaction:** Structured application loggers automatically mask authorization headers, tokens, database passwords, and API keys before writing to stdout or disk.
5. **No Shell Ingestion:** The execution engine does not contain an arbitrary shell execution endpoint. There is no route capable of running bash or powershell strings passed from an LLM.

---

## 15. Current Operational Limitations

AegisOps is an advanced portfolio and demonstration platform with intentionally bounded operational capabilities:

| Domain | Current Implementation Scope | Bounded Limitation |
|---|---|---|
| **Remediation Execution** | Bounded demo remediation against local evaluation simulator on Port 8001; dry-run simulation for all plans. | Does not modify live production cloud infrastructure or execute arbitrary bash commands. |
| **Rollback Execution** | Automated readiness assessment, dry-run simulation, and demo rollback state restoration against Port 8001. | Does not perform unconstrained automated rollbacks against production cloud providers. |
| **Telemetry Ingestion** | Full Prometheus PromQL metrics and Alertmanager webhook alerts. | OpenTelemetry distributed trace correlation is slated for future releases. |
| **Cluster Management** | Read-only diagnostic querying via Prometheus. | Does not mutate Kubernetes manifests or patch live cluster pods. |
| **Identity Provider** | Role-based JWT headers and local development persona switching. | Enterprise SAML / Okta / Azure AD SSO integration requires deployment-specific configuration. |

---

## 16. Roadmap & Future Work

- [ ] **OpenTelemetry Trace Correlation:** Ingest distributed trace spans (OTel) to correlate microservice latency spikes directly with downstream RPC errors.
- [ ] **Kubernetes Read-Only Diagnostic Operator:** Safely retrieve pod logs, describe events, and inspect resource quotas via a scoped, read-only Kubernetes service account.
- [ ] **Automated Post-Mortem Generator:** Generate Markdown and PDF post-incident post-mortems summarizing timeline, metric deltas, root cause analysis, and remediation effectiveness.
- [ ] **Multi-Cluster Federation:** Expand Alertmanager and Prometheus ingestion to aggregate alerts across multi-region cloud topologies.

---

## 17. License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

---

### Summary

**AegisOps demonstrates how Agentic AI can empower Site Reliability Engineers during mission-critical incidents without ever relinquishing deterministic safety boundaries or human operational governance.**
