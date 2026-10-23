# AegisOps Platform Evaluation Framework

Comprehensive evaluation suite for validating end-to-end operational correctness, agentic reasoning quality, safety boundaries, reliability, and performance.

---

## 1. Directory Structure

```text
evaluation/
├── datasets/
│   ├── edge_cases.json           # 15+ edge cases covering telemetry gaps, attacks, and timeouts
│   ├── evaluation_cases.py       # Pydantic data models & dataset loaders
│   └── __init__.py
│
├── scenarios/
│   ├── healthy.json              # Baseline nominal operating conditions
│   ├── high_cpu.json             # Compute saturation telemetry
│   ├── high_latency.json         # API request latency degradation
│   ├── error_spike.json          # 5xx HTTP error surge
│   ├── service_degradation.json  # Multi-vector composite degradation
│   └── __init__.py
│
├── metrics/
│   ├── rubrics.py                # 0-2 qualitative rubrics for Investigation & RCA
│   ├── calculator.py             # Latency percentiles (min/max/mean/p50/p95/p99) & rates
│   └── __init__.py
│
├── runners/
│   ├── evaluate_triage.py        # Severity-to-priority accuracy & escalation decisions
│   ├── evaluate_historical_evidence.py # Timezone awareness, zero preservation, range queries
│   ├── evaluate_investigation.py # Grounded observations vs hypotheses
│   ├── evaluate_rca.py           # Multi-hypothesis RCA & root_cause_confirmed=False
│   ├── evaluate_safety.py        # Deterministic safety validator & adversarial injection
│   ├── evaluate_authorization.py # RBAC, dual-control, plan hash verification
│   ├── evaluate_execution_boundaries.py # Read-only registry & simulation constraints
│   ├── evaluate_verifications_rollbacks.py # Truthful verification & rollback applicability
│   ├── evaluate_reliability.py   # Failure recovery for Prometheus/Gemini outages
│   ├── evaluate_performance.py   # Latency benchmarks (p50/p95/p99)
│   ├── evaluate_cost.py          # Token usage & Gemini cost modeling
│   ├── evaluate_e2e_lifecycle.py # Full 12-stage operational lifecycle test
│   └── __init__.py
│
├── reports/
│   ├── evaluation_summary.json
│   ├── operational_results.json
│   ├── agent_quality_results.json
│   ├── safety_results.json
│   ├── reliability_results.json
│   ├── performance_results.json
│   ├── cost_results.json
│   └── evaluation_report.md
│
└── README.md
```

---

## 2. Evaluation Suites

1. **Operational Lifecycle (`--suite operational`)**:
   - Triage accuracy (P1–P4, case insensitivity, missing field fallbacks).
   - Historical evidence accuracy (timezone awareness, non-finite rejection, zero preservation).
   - End-to-end 12-stage operational workflow pipeline.

2. **Agentic Reasoning Quality (`--suite agents`)**:
   - Investigation agent quality scored against standardized 0-2 rubric.
   - RCA agent quality with mandatory `root_cause_confirmed = False` constraint.

3. **Remediation Safety & Boundaries (`--suite safety`)**:
   - Adversarial prompt injection, banned commands (`rm -rf`, `chmod 777`, `kill -9`).
   - Invariant enforcement: `execution_enabled = False` and `requires_human_approval = True`.
   - RBAC permissions, self-approval prevention, plan hash tamper detection.
   - Truthful rollback readiness: `Rollback: Not Applicable` for read-only operations.

4. **Failure Recovery & Reliability (`--suite reliability`)**:
   - Prometheus connection errors.
   - Gemini quota exhaustion (429) and internal server errors (500).
   - Partial metric availability handling.

5. **Performance & Latency (`--suite performance`)**:
   - Sub-millisecond deterministic decision latency.
   - p50, p95, p99 percentiles over 50 iterations per operation.

6. **Gemini Usage & Cost (`--suite cost`)**:
   - Token accounting across Investigation, RCA, and Remediation Planning.
   - Cost projection based on official Gemini Developer rate cards.

---

## 3. Running the Evaluation Suite (Windows CMD)

### Run All Suites (Default Mocked Mode)
```cmd
uv run python scripts/evaluate_platform.py --suite all --mode mocked
```

### Run Specific Suite
```cmd
uv run python scripts/evaluate_platform.py --suite safety
uv run python scripts/evaluate_platform.py --suite performance
uv run python scripts/evaluate_platform.py --suite operational
```

### Run Live Gemini Evaluation (Bounded to 3 calls)
```cmd
uv run python scripts/evaluate_platform.py --suite agents --mode live --max-gemini-calls 3
```

---

## 4. Mandatory Safety Invariants

| Invariant | Mandatory Value | Purpose |
|---|---|---|
| `root_cause_confirmed` | `False` | Prevents unconfirmed hypotheses from being presented as confirmed root causes |
| `requires_human_review` | `True` | Mandates human operator oversight for all RCA results |
| `execution_enabled` | `False` | Prevents autonomous infrastructure remediation execution |
| `requires_human_approval` | `True` | Mandates explicit engineer authorization for all plans |
| `rollback_execution_enabled`| `False` | Rollback execution is strictly disabled |
| `system_changes_performed` | `False` | Verifies zero mutations occurred during diagnostic/simulation |
