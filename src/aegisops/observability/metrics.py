import time

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.routing import Match, Route

# 1. HTTP Ingress Metrics
HTTP_REQUESTS = Counter(
    "aegisops_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_DURATION = Histogram(
    "aegisops_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

# 2. Incident Ingestion Metrics
INCIDENTS_CREATED = Counter(
    "aegisops_incidents_created_total",
    "Successfully created incidents",
    ["severity"],
)

INCIDENT_INGESTION = Counter(
    "aegisops_incident_ingestion_total",
    "Total incidents ingested by source and severity",
    ["source", "severity"],
)

# 3. Agentic Workflow Observability
WORKFLOW_RUNS = Counter(
    "aegisops_workflow_runs_total",
    "Total agentic workflow runs by status",
    ["status"],
)

WORKFLOW_NODE_DURATION = Histogram(
    "aegisops_workflow_node_duration_seconds",
    "Workflow node duration in seconds",
    ["node"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# 4. Gemini Telemetry & Cost Metrics
GEMINI_REQUESTS = Counter(
    "aegisops_gemini_requests_total",
    "Total Gemini API requests by stage and status",
    ["stage", "status"],
)

GEMINI_REQUEST_DURATION = Histogram(
    "aegisops_gemini_request_duration_seconds",
    "Gemini API request duration in seconds",
    ["stage"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0),
)

GEMINI_TOKENS = Counter(
    "aegisops_gemini_tokens_total",
    "Total Gemini tokens consumed by stage and token type",
    ["stage", "token_type"],
)

# 5. Remediation Lifecycle Metrics
APPROVAL_DECISIONS = Counter(
    "aegisops_approval_decisions_total",
    "Total human remediation approval decisions",
    ["decision"],
)

EXECUTION_REQUESTS = Counter(
    "aegisops_execution_requests_total",
    "Total remediation execution requests",
    ["mode", "operation", "status"],
)

VERIFICATION_REQUESTS = Counter(
    "aegisops_verification_requests_total",
    "Total post-execution verifications by outcome",
    ["outcome"],
)

ROLLBACK_ASSESSMENTS = Counter(
    "aegisops_rollback_assessments_total",
    "Total rollback assessments by readiness category",
    ["readiness"],
)

# 6. Security Denial Tracking
SECURITY_DENIALS = Counter(
    "aegisops_security_denials_total",
    "Total security denials across authentication, CSRF, rate limits, and RBAC",
    ["reason", "endpoint"],
)


def setup_metrics(app: FastAPI) -> None:
    app.mount("/metrics", make_asgi_app())

    @app.middleware("http")
    async def record_metrics(request: Request, call_next):
        start = time.perf_counter()

        response = await call_next(request)

        if request.url.path == "/metrics":
            return response

        path = "unmatched"

        for route in app.routes:
            if isinstance(route, Route):
                match, _ = route.matches(request.scope)

                if match == Match.FULL:
                    path = route.path
                    break

        HTTP_REQUESTS.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()

        HTTP_DURATION.labels(
            method=request.method,
            path=path,
        ).observe(time.perf_counter() - start)

        return response
