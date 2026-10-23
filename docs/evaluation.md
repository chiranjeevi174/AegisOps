# AegisOps — Platform Evaluation & Verification Report

## 1. Evaluation Overview & Methodology

This document summarizes the empirical evaluation of the **AegisOps** agentic incident response platform. The evaluation evaluates deterministic lifecycle correctness, multi-agent AI reasoning quality, safety invariants, operational authorization boundaries, reliability under component failure, deterministic latency benchmarks, and LLM token cost modeling.

### Evaluation Parameters
- **Test Date**: 2026-10-22
- **Suite Target**: `all` (7 suites)
- **Evaluation Mode**: `mocked` (Hermetic evaluation ensuring deterministic assertions without uncontrolled external AI API charges)
- **Target LLM**: `gemini-3.5-flash-lite`
- **Result Status**: **100% PASSED across all 7 suites**

---

## 2. Executive Summary Results

| Evaluation Suite | Status | Key Metric | Target / Benchmark | Result |
|---|---|---|---|---|
| **Operational Lifecycle** | `PASSED` | Triage Accuracy | 100.0% | **100.0%** (9/9 scenarios) |
| **Historical Evidence** | `PASSED` | Telemetry Integrity | 100.0% | **100.0%** pass rate |
| **Agent Quality (Investigation)** | `PASSED` | Metric Grounding | >90.0% | **92.86%** grounded |
| **Agent Quality (RCA)** | `PASSED` | False Confirmation Gate | Confirmed False | **100.0%** (`root_cause_confirmed=False` held) |
| **Remediation Safety** | `PASSED` | Unsafe Rejection Rate | 100.0% | **100.0%** (0 leaks out of 7 adversarial plans) |
| **Authorization Boundaries** | `PASSED` | Dual-Control Pass Rate | 100.0% | **100.0%** enforced |
| **Execution Safeguards** | `PASSED` | Read-Only Invariant | 100.0% | **100.0%** read-only registry |
| **Post-Execution Verification** | `PASSED` | Verification Pass Rate | 100.0% | **100.0%** (`success=False` for simulation) |
| **Rollback Assessment** | `PASSED` | Non-Applicable Invariant | 100.0% | **100.0%** (`not_applicable` for simulations) |
| **Reliability & Recovery** | `PASSED` | Fault Tolerance | 4/4 checks | **4/4 passed (100.0%)** |
| **Performance Benchmarks** | `PASSED` | Triage Latency (p50) | <10.0 ms | **0.000 ms** (Sample size = 50) |
| **Cost & Token Modeling** | `PASSED` | Workflow Tokens | <15,000 | **6,700 tokens / incident** |

---

## 3. Dataset Composition & Scenarios

The evaluation suite utilizes synthetic and structured operational incident datasets located in `evaluation/scenarios/` and `evaluation/datasets/`:

1. **High CPU Utilization (`high_cpu.json`)**: Simulated compute spike (94% CPU utilization, moderate latency impact).
2. **High API Latency (`high_latency.json`)**: Severe response time degradation (2.8s p99 latency, normal CPU).
3. **HTTP Error Spike (`error_spike.json`)**: Elevated HTTP 5xx error rates (35% error ratio, intermittent dropouts).
4. **Service Degradation (`service_degradation.json`)**: Composite multi-signal failure (85% CPU, 4.2s latency, 65% errors, service availability drops to 0).
5. **Healthy Baseline (`healthy.json`)**: Nominal operational telemetry (25% CPU, 80ms latency, 0.1% error rate).
6. **Adversarial Safety Dataset**: 7 adversarial remediation plans containing prompt-injection attempts, destructive shell commands (`rm -rf`, `DROP TABLE`, `kill -9`), unauthenticated remote SSH calls, and falsified incident closure declarations.

---

## 4. Detailed Dimension Analysis

### 4.1. Operational Lifecycle & Triage Accuracy
- **Cases Evaluated**: 9 edge-case and standard alert payloads (P1/Critical, P2/High, P3/Medium, P4/Low, mixed-case severity strings, unmapped severities falling back to default, and missing severity keys).
- **Triage Accuracy**: **100.0%**. Every alert was mapped to the correct internal severity enum and priority level without exceptions.
- **Historical Telemetry Integrity**:
  - Timezone-aware UTC timestamps strictly enforced (naive timestamps rejected).
  - Genuine zero values (`0.0%` CPU or `0` errors) preserved without being dropped or treated as null.
  - Future timestamp clamping verified (timestamps ahead of current server UTC clamped to prevent telemetry drift).
  - Non-finite telemetry values (`NaN`, `Infinity`, `-Infinity`) safely handled without JSON or math crashes.

### 4.2. Agent Quality & Root Cause Analysis (RCA)
- **Telemetry Grounding Rate**: **92.86%**. The Investigation Agent strictly referenced observed Prometheus metric samples without fabricating external unobserved indicators.
- **Hypothesis Classification**: Categorized as `primary_hypothesis`, `contributing_factors`, and `alternative_hypotheses`.
- **Root Cause Uncertainty Preservation**: In 100.0% of test runs, `root_cause_confirmed = False` was preserved. The agent explicitly recognized data limitations and prohibited premature closure.

### 4.3. Remediation Safety & Execution Boundaries
- **Adversarial Plans Blocked**: 7 of 7 (100.0% rejection rate).
- **Unsafe Command Leaks**: **0**.
- **Safe Advisory Plans Accepted**: 2 of 2 (100.0% acceptance rate for non-destructive observation and config-review plans).
- **Execution Safeguards**:
  - 100% of operations in the execution registry are read-only.
  - Zero state-mutating commands (e.g. `systemctl restart`, `kubectl delete pod`, `docker rm`) are supported or present in the execution engine.
  - Arbitrary shell execution is completely absent from the codebase.

### 4.4. Authorization & Human-in-the-Loop Governance
- **Role-Based Access Control (RBAC)**: Only callers possessing the `approver` role can approve requests. Callers with `operator` or `requester` roles are rejected with HTTP 403.
- **Dual-Control Enforcement**: An operator attempting to approve their own remediation request (`requester == approver`) is strictly blocked.
- **Tamper-Evident SHA-256 Hash**: If an approved plan payload is modified after authorization, execution is refused due to cryptographic hash mismatch.
- **Expiration Policy**: Approvals older than 24 hours automatically fail closed (`status: expired`).

### 4.5. Post-Execution Verification & Rollback Assessment
- **Post-Execution Verification**: Evaluated deterministic baseline comparison. Because executions are non-destructive simulations, the verification outcome truthfully outputs `not_applicable` with `remediation_success = False`.
- **Rollback Readiness Assessment**: Deterministically confirms zero mutations were performed on live systems, reporting `readiness_status: NOT_APPLICABLE` and maintaining `rollback_execution_enabled: False`.

### 4.6. Reliability & Error Recovery
Tested platform behavior under synthetic dependency failure injections:
1. **Prometheus Unavailability**: FastAPI backend gracefully falls back to cached/empty telemetry without unhandled 500 errors.
2. **Gemini API Error / Timeout**: LangGraph workflow catches upstream AI API exceptions, records failure event, and yields safe degraded remediation recommendations without crashing.
3. **Database Disconnection**: Health checks (`/health/ready`) immediately report `database: unhealthy` with HTTP 503 while liveness remains green.
4. **Malformed Alertmanager Webhook**: Schema validation rejects invalid payloads with HTTP 422 before reaching the agent workflow.

### 4.7. Deterministic Latency Benchmarks (Sample Size = 50)
Deterministic decision and safety components benchmarked on local test hardware:
- **Triage Decision Latency**: p50 = `0.000 ms`, p95 = `0.010 ms`
- **Safety Validation Latency**: p50 = `0.005 ms`, p95 = `0.012 ms`
- **Plan Hash Verification Latency**: p50 = `0.013 ms`, p95 = `0.025 ms`
- **Rollback Assessment Latency**: p50 = `0.008 ms`, p95 = `0.019 ms`

### 4.8. Gemini Token Usage & Cost Modeling
- **Target Model**: `gemini-3.5-flash-lite`
- **Estimated Tokens per Incident Workflow**: ~6,700 tokens (Investigation: ~3,200 tokens, RCA: ~2,100 tokens, Remediation Planning: ~1,400 tokens).
- **Cost Policy**: Model pricing for `gemini-3.5-flash-lite` is reported as unavailable pending official developer rate cards; synthetic token counts are tracked deterministically to prevent unexpected charges.

---

## 5. Scope Constraints & Production Boundaries

> [!IMPORTANT]
> - All AI evaluations were executed against synthetic scenarios and mock adapters. Real-world LLM output may exhibit non-deterministic variance in natural language phrasing.
> - AegisOps does not perform automated autonomous remediation on infrastructure. Execution is restricted to simulations and server-allowlisted read-only diagnostics.
> - High evaluation pass rates demonstrate architectural adherence to safety boundaries, not a guarantee of universal security against zero-day threats.

---

## 6. Reproduction Command

To execute the entire 7-suite evaluation hermetically:

```cmd
uv run python scripts/evaluate_platform.py --suite all --mode mocked
```
