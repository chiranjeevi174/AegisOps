# AegisOps Observability & Operational Monitoring Guide

## 1. Overview

AegisOps provides production-oriented observability designed for site reliability engineers (SREs). In Step 16, the platform was upgraded with:
1. Structured JSON application logging with automated sensitive data redaction.
2. Request and incident correlation propagation (`X-Request-ID`).
3. Low-cardinality Prometheus telemetry covering API ingress, agentic workflows, Gemini LLM calls, and HITL safety decisions.
4. Pre-provisioned Grafana dashboards and Prometheus alerting rules designed to avoid recursive feedback loops.
5. Strict liveness (`/health/live`) and dependency readiness (`/health/ready`) probes.

---

## 2. Structured JSON Logging Architecture

All backend application logs are emitted as single-line JSON objects to standard output/error, allowing ingestion by log aggregators (e.g., Fluent Bit, Logstash, Datadog, CloudWatch).

### Standard Schema Fields:
```json
{
  "timestamp": "2026-10-22T06:47:43.763129+00:00",
  "level": "INFO",
  "service": "aegisops",
  "environment": "development",
  "event": "workflow_node_complete",
  "request_id": "req_8471b045e4564ae1",
  "correlation_id": "corr_c2910fa9831c",
  "incident_id": "293ccfab-47eb-46fb-860f-8732d1969f79",
  "execution_id": null,
  "node_name": "root_cause_analysis",
  "duration_seconds": 1.428,
  "message": "Workflow node completed successfully"
}
```

### Sensitive Data Redaction:
The custom `JSONFormatter` automatically scrubs sensitive parameters from log records and stack traces before formatting:
- Bearer tokens: `Bearer [REDACTED_TOKEN]`
- Session cookies: `aegisops_session=[REDACTED_COOKIE]`
- Passwords and API keys: `password="[REDACTED]"`, `api_key="[REDACTED]"`

---

## 3. Request Correlation & Context Propagation

Every HTTP request is assigned a unique identifier to trace execution through middleware, route handlers, async worker tasks, database queries, and agentic workflows:

1. **Incoming Request ID Validation**: If an incoming request provides `X-Request-ID` matching `^[a-zA-Z0-9_\-\.]{1,64}$`, it is preserved. Invalid or missing headers trigger automatic generation of a new ID (`req_<hex>`).
2. **Context Variable Storage**: The ID is stored in Python `contextvars.ContextVar`, accessible across all async tasks without parameter passing.
3. **Response Header Injection**: The response echoes `X-Request-ID`.
4. **Lifecycle Traceability**: Workflow events correlate `incident_id`, `approval_id`, and `execution_id` in structured logs.

---

## 4. Prometheus Application Metrics

AegisOps exports Prometheus metrics on `GET /metrics`. All metrics adhere to strict low-cardinality constraints: labels never contain incident UUIDs, user tokens, URLs, raw prompts, or arbitrary error strings.

### Key Metrics Reference:

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `aegisops_http_requests_total` | Counter | `method`, `path`, `status` | Total HTTP requests processed |
| `aegisops_http_request_duration_seconds` | Histogram | `method`, `path` | Request response latency (buckets: 5ms to 10s) |
| `aegisops_incidents_created_total` | Counter | `severity` | Total incidents created |
| `aegisops_workflow_runs_total` | Counter | `status` | Agentic LangGraph workflow executions (`succeeded`, `failed`) |
| `aegisops_workflow_node_duration_seconds` | Histogram | `node` | Duration of each workflow node (`triage`, `rca`, etc.) |
| `aegisops_gemini_requests_total` | Counter | `stage`, `status` | Gemini LLM calls by workflow stage |
| `aegisops_gemini_request_duration_seconds` | Histogram | `stage` | Latency of Gemini API invocations |
| `aegisops_gemini_tokens_total` | Counter | `stage`, `token_type` | Tokens consumed (`input`, `output`) |
| `aegisops_approval_decisions_total` | Counter | `decision` | Human approval decisions (`approved`, `rejected`, `revision`) |
| `aegisops_execution_requests_total` | Counter | `mode`, `operation`, `status` | Simulated & diagnostic execution outcomes |
| `aegisops_verification_requests_total` | Counter | `outcome` | Post-execution verification results |
| `aegisops_rollback_assessments_total` | Counter | `readiness` | Rollback readiness assessments |
| `aegisops_security_denials_total` | Counter | `reason`, `endpoint` | Security denials (RBAC, CSRF, rate limits) |
| `aegisops_dependency_health_status` | Gauge | `dependency` | Core dependency health (`1` = ready, `0` = unready) |

---

## 5. Grafana Dashboard

A dedicated dashboard is provisioned at `/etc/grafana/provisioning/dashboards/aegisops_platform_overview.json`:
- **UID**: `aegisops-overview`
- **Datasource**: `aegisops-prometheus` (`http://prometheus:9090`)

### Dashboard Panels:
1. **HTTP Ingress & Performance**: Request rate (req/s), HTTP 5xx error rate (%), API response latency quantiles (p50, p95).
2. **Agentic Workflows & AI Reliability**: LangGraph workflow run statuses, node durations, Gemini request volume, and token consumption by stage.
3. **Security & Safety Enforcements**: Security denial rates by reason, HITL approval decision rates, and execution/verification outcomes.
4. **Platform Infrastructure Health**: Stat panel showing real-time health of PostgreSQL, Prometheus, and Gemini configuration.

---

## 6. Alerting Rules & Feedback Loop Prevention

Prometheus alerts are configured in `infrastructure/prometheus/alerts.yml`.

### Alert Rule Definitions:
1. `AegisOpsSustainedAPIErrorRate`: Fires if 5xx errors exceed 5% over 5 minutes (Severity: `critical`).
2. `AegisOpsElevatedAPILatency`: Fires if p95 latency exceeds 2 seconds over 2 minutes (Severity: `warning`).
3. `AegisOpsDependencyReadinessFailure`: Fires if PostgreSQL or Prometheus readiness fails for 1 minute (Severity: `critical`).
4. `AegisOpsWorkflowFailureRate`: Fires if workflow failures exceed 20% over 2 minutes (Severity: `high`).
5. `AegisOpsSecurityDenialSpike`: Fires if security denials exceed 10/s over 1 minute (Severity: `warning`).

### Loop Prevention Architecture:
To prevent AegisOps from triggering recursive synthetic incident loops on its own internal operational alerts:
- Platform alerts are tagged with `service: aegisops` and `alert_category: platform`.
- `alertmanager.yml` routes `service: aegisops` to `platform-ops-alerts` (deadletter / ops notifications) rather than forwarding to `aegisops-webhook`.

---

## 7. Health & Readiness Endpoints

AegisOps implements two distinct health endpoints for container orchestrators (e.g. Kubernetes, Docker Compose):

### 1. Liveness Probe: `GET /api/v1/health/live` (or `/health`)
- Fast, non-blocking check.
- Returns `HTTP 200 OK` with `{"status": "healthy", "service": "aegisops"}`.
- Used to restart a crashed or deadlocked container.

### 2. Readiness Probe: `GET /api/v1/health/ready`
- Performs bounded dependency checks with a strict 2-second timeout per dependency:
  - **PostgreSQL**: Executes `SELECT 1` on the async session pool.
  - **Prometheus**: Verifies HTTP connectivity to `http://localhost:9090/-/healthy`.
  - **Gemini Config**: Verifies API key and model configuration without initiating a paid API call.
- Returns `HTTP 200 OK` when dependencies are healthy, or `HTTP 503 Service Unavailable` if a critical dependency (PostgreSQL) is down.

---

## 8. Operational Troubleshooting Guide

### Issue: API returns HTTP 429 Too Many Requests
- Check the `Retry-After` header for cooldown period.
- Verify whether client IP is behind a proxy and configure `TRUSTED_PROXIES` in `.env` if legitimate requests are sharing an ingress IP.

### Issue: Browser dashboard receives HTTP 403 Forbidden with "Invalid or missing CSRF token"
- Confirm frontend sent `X-CSRF-Token` header.
- Ensure browser has not blocked `aegisops_csrf` cookie.
- If testing cross-origin locally, verify client port is listed in `CORS_ALLOWED_ORIGINS`.

### Issue: Prometheus readiness check fails
- Check Docker status: `docker ps | grep aegisops-prometheus`.
- Verify port 9090 is accessible from host: `curl http://localhost:9090/-/healthy`.
