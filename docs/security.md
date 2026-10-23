# AegisOps Security Architecture & Production Hardening Guide

## 1. Executive Summary

AegisOps is an Agentic SRE and Autonomous Incident Response Platform designed with strict defense-in-depth, least-privilege, and human-in-the-loop (HITL) architectural boundaries. In Step 16, enterprise security hardening and operational safety guardrails were implemented across authentication, cross-site request forgery (CSRF) defense, role-based access control (RBAC), targeted rate limiting, and agentic AI prompt-injection boundaries.

---

## 2. Authentication Model

AegisOps supports dual-mode authentication designed to separate automated API clients from browser-mediated operator sessions:

1. **Bearer Token Authentication**:
   - Used by automated API clients, CI/CD pipelines, and the Alertmanager webhook receiver.
   - Header format: `Authorization: Bearer <token>`.
   - Token lookup uses constant-time comparison (`hmac.compare_digest`) to prevent timing attacks.
   - Bearer requests are stateless and exempt from browser CSRF checks.

2. **Backend-Mediated Session Cookies**:
   - Used by the React Operator Dashboard.
   - Session establishment: `POST /api/v1/auth/session` validates credentials and issues an `HttpOnly`, `SameSite=Lax` session cookie (`aegisops_session`).
   - Session lifetime is bounded (default: 86,400s / 24h).
   - In production environments, the cookie is marked `Secure` (HTTPS only).
   - JavaScript code running in the browser cannot read or modify the `aegisops_session` cookie, preventing credential exfiltration via cross-site scripting (XSS).

---

## 3. Development vs. Production Persona Restrictions

During local testing, AegisOps provides a development persona switcher to facilitate testing of distinct SRE roles (e.g., operator, approver, requester).

### Production Safeguards:
- **Server-Side Enforcement**: Persona switching is controlled by `enable_dev_persona_switching: bool` in `Settings` and is strictly gated on `settings.environment == "development"`.
- **Immediate Rejection**: In non-development environments or when disabled, `GET /api/v1/auth/actors` and `POST /api/v1/auth/session` with an `identity` parameter immediately return `HTTP 403 Forbidden`.
- **Client Independence**: The frontend persona switcher UI cannot be enabled by modifying client-side state, Vite environment flags, or request headers.
- **Architectural Boundary**: Development personas are strictly for local testing and do not replace production identity providers (IdPs/OIDC).

---

## 4. CSRF Defense Architecture

AegisOps enforces session-bound Double-HMAC CSRF validation for all state-changing HTTP requests (`POST`, `PUT`, `DELETE`, `PATCH`):

1. **Session-Bound Cryptographic Token**:
   - CSRF tokens are computed as `HMAC-SHA256(csrf_secret_key, session_token)`.
   - Tokens cannot be forged without knowing both the session token and the server-side CSRF secret key.
   - A companion non-HttpOnly cookie (`aegisops_csrf`) and response payload provide the token to the frontend client.

2. **Validation Pipeline**:
   - On state-changing requests, `get_current_actor` verifies:
     1. Origin/Referer header matches configured trusted domains (`cors_allowed_origins`).
     2. `X-CSRF-Token` header matches the expected HMAC for the authenticated session using constant-time comparison.
   - If the token is missing, invalid, or issued for a different session, the request is rejected with `HTTP 403 Forbidden` and logged as a security denial.
   - Logout (`POST /api/v1/auth/logout`) is explicitly protected by CSRF validation to prevent forced-logout attacks.

---

## 5. Role-Based Access Control (RBAC) Matrix

AegisOps implements strict authorization checks before any operation is evaluated or executed:

| Endpoint / Operation | Minimum Required Role | Denial Response |
| :--- | :--- | :--- |
| `GET /api/v1/overview` | `viewer` | `401 Unauthorized` |
| `GET /api/v1/incidents` | `viewer` | `401 Unauthorized` |
| `POST /api/v1/incidents/{id}/analyze` | `operator`, `requester`, `approver`, `admin` | `403 Forbidden` (Viewers blocked) |
| `POST /api/v1/incidents/{id}/approvals` | `requester`, `admin` | `403 Forbidden` |
| `POST /api/v1/approvals/{id}/approve` | `approver`, `admin` (Self-approval blocked) | `403 Forbidden` |
| `POST /api/v1/approvals/{id}/reject` | `approver`, `admin` | `403 Forbidden` |
| `POST /api/v1/executions/simulate` | `operator`, `executor`, `admin` | `403 Forbidden` |
| `POST /api/v1/executions/diagnose` | `operator`, `executor`, `admin` | `403 Forbidden` |
| `POST /api/v1/executions/{id}/verifications` | `verifier`, `operator`, `admin` | `403 Forbidden` |
| `POST /api/v1/executions/{id}/rollback-assessments` | `rollback_assessor`, `operator`, `admin` | `403 Forbidden` |

### Key Authorization Invariants:
1. **Self-Approval Prevention**: The requester who submitted an approval request cannot approve their own plan (`requester_id != approver_id`).
2. **Plan Integrity**: Any modification or tampering with a remediation plan invalidates its SHA-256 hash, causing approval decisions or execution requests to fail closed.
3. **Execution Prohibition**: Rollback assessment authorization does not grant rollback execution permissions. Actual remediation and rollback execution remain disabled across all operations.

---

## 6. Targeted API Rate Limiting

To prevent brute force, denial of service, and excessive LLM billing, targeted rate limiting is applied via sliding-window token counters:

| Endpoint Category | Default Limit | Window | Rate Limit Key |
| :--- | :--- | :--- | :--- |
| Authentication (`/auth/session`) | 10 req | 60s | Client IP |
| Webhook Ingestion (`/webhooks/alertmanager`) | 60 req | 60s | Client IP |
| AI Analysis (`/incidents/{id}/analyze`) | 15 req | 60s | Client IP / Actor |
| Approval Decisions (`/approvals/{id}/*`) | 30 req | 60s | Actor Identity |
| Diagnostic & Sim Execution (`/executions/*`) | 30 req | 60s | Actor Identity |
| Verification & Rollback Assessments | 30 req | 60s | Actor Identity |

### Headers & Responses:
- Exceeded limits return `HTTP 429 Too Many Requests`.
- Standard headers included: `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Untrusted forwarded headers are ignored; `X-Forwarded-For` is only parsed when the direct peer IP is in `trusted_proxies`.

---

## 7. Agentic AI Safety & Prompt-Injection Boundaries

External inputs (such as incident descriptions, alert annotations, and Prometheus query outputs) are treated as **untrusted data**.

### Safeguards:
1. **Separation of Instructions & Evidence**: LangGraph nodes use structured prompt boundaries separating system directives from external evidence.
2. **Deterministic Adversarial Filter**: An automated security validator checks remediation action descriptions and command arguments for adversarial patterns:
   - Instruction overrides: `"ignore previous instructions"`, `"system override"`, `"disregard"`.
   - Role spoofing: `"approved by administrator"`, `"role: admin"`, `"actor: sre-admin"`.
   - Unauthorized status mutation: `"mark incident as resolved"`, `"close incident"`.
   - Destructive command patterns: `"rm -rf"`, `"format c:"`, `"cat .env"`, `"drop database"`.
   - Plan integrity bypass attempts: `"bypass plan hash"`, `"skip verification"`.
3. **Deterministic Safety Validation**: LLM output is parsed into strict Pydantic schemas (`RemediationPlan`, `RemediationAction`). Schema validators reject plans where `requires_human_approval == False` or `execution_enabled == True`.
4. **Execution Registry Isolation**: Only pre-registered read-only diagnostic operations are executable in live mode; all remediation and rollback operations are restricted to simulation mode.

---

## 8. Secrets Management & Credential Rotation

- **No Secrets in Bundles**: The frontend Vite configuration contains zero API keys, secrets, or privileged tokens.
- **Environment Isolation**: Application credentials (`ALERTMANAGER_WEBHOOK_TOKEN`, `GEMINI_API_KEY`, `POSTGRES_PASSWORD`, `CSRF_SECRET_KEY`) are managed via Pydantic `SecretStr`.
- **Credential Rotation Guidelines**:
  - Development tokens in `.env.example` are sample values only and must be replaced in staging and production.
  - In production, set `CSRF_SECRET_KEY` and `SESSION_SECRET_KEY` to high-entropy 256-bit random hex strings.
  - Rotate Alertmanager webhook tokens periodically by updating `/etc/alertmanager/webhook_token.txt` and restarting the Alertmanager service.

---

## 9. Known Limitations & Production Roadmap

1. **Distributed Rate Limiting**: The current rate limiter uses process-local memory. For multi-replica Kubernetes deployments, a Redis-backed token bucket or an API Gateway (e.g., Envoy/Kong) is recommended.
2. **Identity Management**: Development persona switching is local-only. Production deployments must integrate an enterprise OIDC/SAML provider.
3. **Audit Log Persistence**: Audit events are persisted to PostgreSQL. For compliance in regulated environments, write-once-read-many (WORM) storage or external SIEM shipping (e.g., Splunk/Datadog) should be enabled.
