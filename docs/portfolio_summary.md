# AegisOps — Portfolio, Resume & Technical Interview Guide

## 1. Project Overview (120 Words)

**AegisOps** is an autonomous incident response and agentic SRE platform engineered to accelerate Mean Time to Detect (MTTD) and Mean Time to Investigate (MTTI) while preserving strict human-in-the-loop safety boundaries. Built with **FastAPI**, **PostgreSQL**, **LangGraph**, and **Google Gemini**, the platform ingests alerts from **Prometheus** and **Alertmanager**, orchestrates multi-agent investigations, gathers time-series telemetry, and generates evidence-grounded root-cause hypotheses with non-destructive remediation proposals.

To eliminate operational risk, AegisOps enforces an immutable safety architecture: every remediation plan is cryptographically SHA-256 hashed, gated behind authenticated dual-control approval (`requester != approver`), and restricted to simulation mode or allowlisted read-only diagnostics. The platform features an operator dashboard built in **React** and **TypeScript**, packaged via **Docker Compose** for reproducible deployment.

---

## 2. Resume Version (Concise Bullet Points)

- **Architected and developed an Agentic SRE & Incident Response platform** using FastAPI, LangGraph, and Google Gemini, automating alert triage, Prometheus telemetry correlation, and evidence-grounded root cause analysis across 5 failure scenarios.
- **Implemented zero-trust execution safety boundaries and dual-control approval gateways**, enforcing cryptographic SHA-256 plan integrity, strict RBAC separation of duties (`requester != approver`), and 100% read-only simulation execution to eliminate destructive operational mutations.
- **Engineered an enterprise containerized architecture and deterministic evaluation suite** across Docker Compose, PostgreSQL 17, Nginx, and React 18, achieving 100% pass rates across 245 backend regression tests, 15 frontend tests, and 7 platform evaluation suites.

---

## 3. Technical Interview Deep Dive

### 3.1. Why was AegisOps created?
Traditional incident response is hindered by two extremes: slow manual triage causing prolonged outages, or reckless automated scripts that risk compounding failures by executing destructive actions without sufficient context. AegisOps was built to solve this tension: leveraging LLM agentic reasoning for complex telemetry correlation and hypothesis generation, while strictly containing execution within deterministic, human-gated, non-destructive boundaries.

### 3.2. What makes it "Agentic AI" rather than a simple chatbot or script?
AegisOps does not merely answer user prompts; it operates as an autonomous, multi-stage state machine driven by external environmental triggers (Alertmanager webhooks). The workflow coordinates specialized agents:
- **Triage Agent**: Evaluates signal properties and determines severity.
- **Evidence Collector**: Gathers real-time Prometheus metrics.
- **Historical Evidence Collector**: Pulls structured time-window telemetry with NaN/zero handling.
- **Investigation & RCA Agents**: Iteratively correlate telemetry, construct hypotheses, and evaluate competing explanations.
- **Safety Validator**: Deterministically validates proposed recommendations against security policies before generating human approval requests.

### 3.3. How does LangGraph coordinate the workflow?
LangGraph models the incident response lifecycle as a directed state graph (`StateGraph`). The incident state flows through deterministic nodes and conditional edges. LangGraph maintains immutable state progression, handles retries and fallback paths when external dependencies degrade, and enforces structured transitions from alert ingestion through to safety validation.

### 3.4. How does evidence-grounded RCA work?
A common vulnerability of LLMs in DevOps is hallucinating imaginary metrics or premature conclusions. AegisOps mitigates this by strictly separating metric collection from inference:
1. Telemetry is collected into structured JSON envelopes containing timestamped float arrays.
2. The Gemini prompt strictly instructs the model to cite only observed Prometheus metric values.
3. The schema enforces that root causes are categorized as hypotheses, with the system invariant `root_cause_confirmed = False` permanently maintained to prevent premature closure without human verification.

### 3.5. Why is human approval mandatory?
In production infrastructure, autonomous state mutation (reboots, config overwrites, scaling, rollbacks) without human oversight carries catastrophic tail risk. AegisOps adopts the **Aviation Principle**: AI acts as the co-pilot diagnosing conditions and proposing navigational adjustments, but the human Captain retains sole authority to approve and initiate action. Furthermore, AegisOps enforces **dual-control separation of duties**: the engineer who requested a remediation plan cannot approve it.

### 3.6. How does the execution safety boundary work?
AegisOps establishes three concentric rings of execution safety:
1. **Cryptographic Immutability**: The approved plan is SHA-256 hashed upon creation. Before execution, the hash is recomputed against the active database record. Any mutation aborts execution.
2. **Deterministic Allowlist Registry**: The execution dispatcher only supports registered, server-allowlisted operations. There is no generic `eval()`, shell executor, or SSH transport.
3. **Simulation Default**: Remediations default to dry-run simulations. Read-only live diagnostics (e.g. querying Prometheus) are restricted and require explicit operational configuration. Live infrastructure rollback execution is disabled by design.

### 3.7. How was platform evaluation conducted?
The platform was validated across a 7-suite evaluation framework (`scripts/evaluate_platform.py`):
1. **Operational Lifecycle**: Triage accuracy across 9 severity permutations.
2. **Historical Evidence**: Zero-preservation, timezone validation, and NaN filtering.
3. **Agent Quality**: Metric grounding (>92%) and hypothesis classification.
4. **Remediation Safety**: 100% rejection of 7 adversarial plans (prompt-injections, destructive bash scripts).
5. **Authorization Boundaries**: RBAC roles and self-approval block validation.
6. **Reliability**: Fault recovery under simulated Prometheus and database dropouts.
7. **Performance & Cost**: Deterministic latency (<0.02ms) and Gemini token modeling (~6,700 tokens/incident).

### 3.8. How do observability and Docker deployment work?
The platform is packaged into an isolated multi-container stack (`aegisops-prod`):
- **PostgreSQL 17**: Internal database with zero exposed host ports.
- **FastAPI Backend**: Runs behind Nginx reverse proxy with health check probes.
- **Prometheus & Grafana**: Collects and visualizes platform telemetry, agent duration, and incident rates.
- **Alertmanager**: Dispatches signed webhooks with bearer tokens.
- **Nginx & React SPA**: Serves production-optimized static assets with security headers (`nosniff`, `DENY`, `no-store`).

---

## 4. Architectural Trade-offs & Limitations

| Trade-off | Choice Made | Alternative Considered | Engineering Rationale |
|---|---|---|---|
| **Execution Autonomy** | Simulation and read-only diagnostics only | Full autonomous shell / Kubernetes execution | Eliminates catastrophic risk of automated infrastructure outages; aligns with real-world enterprise compliance. |
| **LLM Model** | Google Gemini Flash Lite | Local self-hosted LLM (e.g. Llama 3) | Sub-second inference latency and cost efficiency; self-hosted models require dedicated GPU hardware unavailable in lightweight environments. |
| **Persistence** | PostgreSQL + Async SQLAlchemy | Document Store (MongoDB) or Time-Series only | Relational integrity and ACID transactions are critical for audit logs, approval tracking, and dual-control enforcement. |
| **Evaluation Mode** | Hermetic mock evaluation | Pure live Gemini API calls | Guarantees deterministic, reproducible test runs and regression checking without financial cost or external rate limits. |
