# AegisOps — Complete Frontend Control Inventory

**Audit Date:** 2026-10-22
**Target Environment:** Local Development (`http://localhost:5173`)
**Backend API:** FastAPI (`http://127.0.0.1:8000/api/v1`)
**Telemetry Simulator:** Prometheus Metrics (`http://127.0.0.1:8001/metrics`)
**Observability Stack:** Prometheus (`:9090`), Grafana (`:3000`), Alertmanager (`:9093`)

---

## 1. Global Shell & Navigation Controls (`AppLayout`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Global Shell | `Sidebar` | Overview Nav Link | Link (`NavLink`) | Navigates to `/` (Dashboard) | None (Public Authenticated) | `GET /overview` | Browser Click | Route `/` active, Dashboard rendered | PASS |
| Global Shell | `Sidebar` | Incidents Nav Link | Link (`NavLink`) | Navigates to `/incidents` with open badge | None | `GET /incidents` | Browser Click | Route `/incidents` active, badge matches | PASS |
| Global Shell | `Sidebar` | Investigations Nav Link | Link (`NavLink`) | Navigates to `/investigations` | None | `GET /incidents` | Browser Click | Route `/investigations` active | PASS |
| Global Shell | `Sidebar` | Remediation Plans Nav Link | Link (`NavLink`) | Navigates to `/remediation` | None | `GET /approvals` | Browser Click | Route `/remediation` active | PASS |
| Global Shell | `Sidebar` | Approvals Nav Link | Link (`NavLink`) | Navigates to `/approvals` with pending badge | None | `GET /approvals` | Browser Click | Route `/approvals` active, badge matches | PASS |
| Global Shell | `Sidebar` | Executions Nav Link | Link (`NavLink`) | Navigates to `/executions` | None | `GET /executions` | Browser Click | Route `/executions` active | PASS |
| Global Shell | `Sidebar` | Verifications Nav Link | Link (`NavLink`) | Navigates to `/verifications` | None | `GET /verifications` | Browser Click | Route `/verifications` active | PASS |
| Global Shell | `Sidebar` | Rollbacks Nav Link | Link (`NavLink`) | Navigates to `/rollbacks` | None | `GET /rollback-assessments` | Browser Click | Route `/rollbacks` active | PASS |
| Global Shell | `Sidebar` | Audit History Nav Link | Link (`NavLink`) | Navigates to `/audit` | None | `GET /audit/events` | Browser Click | Route `/audit` active | PASS |
| Global Shell | `Sidebar` | Settings Nav Link | Link (`NavLink`) | Navigates to `/settings` | None | `GET /overview/settings` | Browser Click | Route `/settings` active | PASS |
| Global Shell | `Sidebar` | Grafana External Link | External Link (`<a>`) | Opens Grafana UI (`:3000`) in new tab | None | Direct Link | Browser Click | External link target set correctly | PASS |
| Global Shell | `Sidebar` | Persona Switcher Button | Button (`<button>`) | Opens `PersonaSwitcherModal` | Dev Mode (`enable_dev_persona_switching`) | `GET /auth/actors` | Browser Click | Modal opens with actor list | PASS |
| Global Shell | `Header` | Environment Badge | Static Display | Shows `development` environment | None | None | Visual Inspection | Displays `development` | PASS |
| Global Shell | `Header` | API Status Indicator | Status Badge | Shows `Healthy` with green pulsing dot | None | `GET /health/live` | Visual Inspection | Green pulse dot & "Healthy" | PASS |
| Global Shell | `Header` | Prometheus Telemetry Badge | Status Badge | Shows `Live Connected` or `Local Standby` | None | `GET /overview` | Visual Inspection | Shows `Live Connected` | PASS |
| Global Shell | `Header` | Active Persona Badge | Status Badge | Displays active identity and roles | None | `GET /auth/me` | Visual Inspection | Shows `sre-operator-dan / executor+operator+1` | PASS |
| Global Shell | `Header` | Refresh Action Button | Icon Button (`<button>`) | Invalidates TanStack Query cache & refetches | None | Multiple (`/overview`, etc.) | Browser Click | Icon spins, queries refreshed | PASS |
| Global Shell | `PersonaSwitcherModal` | Actor Select Buttons | List Item Buttons | Switches authenticated persona via session | Dev Mode | `POST /auth/session` | Browser Click | Session updated, permissions refreshed | PASS |
| Global Shell | `PersonaSwitcherModal` | Custom Token Input & Form | Form / Input | Logs in using custom bearer token string | None | `POST /auth/session` | Form Submit | Validates token, updates session | PASS |
| Global Shell | `PersonaSwitcherModal` | Close Modal Button | Icon Button | Closes modal dialog | None | None | Click Close (X / Backdrop / ESC) | Modal closes cleanly | PASS |

---

## 2. Page 1 — Overview Dashboard (`/`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Overview | `SafetyBanner` | Safety Guardrails Alert | Static Banner | Displays deterministic guardrail guarantees | None | None | Visual Inspection | Renders guardrail summary banner | PASS |
| Overview | Metric Card 1 | Open Incidents Card | Metric Card | Displays count of open vs total incidents | None | `GET /overview` | Visual Inspection | Displays count matching DB query | PASS |
| Overview | Metric Card 2 | Pending Approvals Card | Metric Card | Displays pending vs historical approvals count | None | `GET /overview` | Visual Inspection | Displays count matching DB query | PASS |
| Overview | Metric Card 3 | Completed Executions Card | Metric Card | Displays total executions and verified count | None | `GET /overview` | Visual Inspection | Displays count matching DB query | PASS |
| Overview | Metric Card 4 | Service Availability Card | Metric Card | Displays live telemetry uptime % and status | None | `GET /overview` | Visual Inspection | Displays 100% (Prometheus live) | PASS |
| Overview | Telemetry Chart | Grafana Deep Link | External Link (`<a>`) | Opens Grafana UI (`:3000`) | None | Direct Link | Browser Click | Opens Grafana in new tab | PASS |
| Overview | Telemetry Chart | Availability History AreaChart | Recharts Chart | Renders live samples of `aegisops_sim_service_up` | None | `GET /overview/telemetry` | Visual & Hover | Renders stepAfter area chart with tooltips | PASS |
| Overview | Severity Pie | Severity Distribution Chart | Recharts PieChart | Displays slice per severity with colored badges | None | `GET /overview` | Visual & Hover | Interactive donut chart with tooltips | PASS |
| Overview | Incidents Table | View All Incidents Button | Link Button (`<Link>`) | Navigates to `/incidents` table | None | None | Browser Click | Navigates to `/incidents` | PASS |
| Overview | Incidents Table | Incident Title Link | Link (`<Link>`) | Navigates to `/incidents/:id` detail | None | None | Browser Click | Navigates to selected incident detail | PASS |
| Overview | Incidents Table | Inspect Button | Secondary Button | Navigates to `/incidents/:id` detail | None | None | Browser Click | Navigates to selected incident detail | PASS |

---

## 3. Page 2 — Incident Management (`/incidents`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Incidents | Header | Create Incident Button | Primary Button | Opens Create Incident modal dialog | None | None | Browser Click | Modal opens | PASS |
| Incidents | Filter Bar | Search Input Field | Text Input (`<input>`) | Filters incident rows by title/desc/UUID | None | Client-side filter | Typing query | Table live-filters rows | PASS |
| Incidents | Filter Bar | Severity Filter Dropdown | Select (`<select>`) | Filters by `critical`, `high`, `medium`, `low` | None | Client-side filter | Option change | Table updates to matching severity | PASS |
| Incidents | Filter Bar | Status Filter Dropdown | Select (`<select>`) | Filters by `open`, `investigating`, `resolved` | None | Client-side filter | Option change | Table updates to matching status | PASS |
| Incidents | Table | Incident Title Links | Link (`<Link>`) | Opens incident detail view | None | None | Browser Click | Navigates to `/incidents/:id` | PASS |
| Incidents | Table | Inspect Action Buttons | Secondary Button | Opens incident detail view | None | None | Browser Click | Navigates to `/incidents/:id` | PASS |
| Incidents | Table | Empty State Display | EmptyState | Shows "No Incidents Match Filter" on no results | None | None | Set non-existent query | EmptyState renders | PASS |
| Incidents | Create Modal | Incident Title Input | Form Input | Validates min 3 chars, required field | None | None | Input + Submit | Validation errors show if empty | PASS |
| Incidents | Create Modal | Description Textarea | Textarea | Validates min 5 chars, required field | None | None | Input + Submit | Validation errors show if empty | PASS |
| Incidents | Create Modal | Severity Selector | Form Select | Selects initial severity tier | None | None | Select change | Updates form value | PASS |
| Incidents | Create Modal | Cancel Button | Ghost Button | Closes modal and resets form state | None | None | Browser Click | Modal closes cleanly | PASS |
| Incidents | Create Modal | Submit Incident Button | Submit Button | Submits synthetic incident creation payload | None | `POST /incidents` | Form Submit | Incident created, appears in table | PASS |

---

## 4. Page 3 — Incident Detail (`/incidents/:id`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Incident Detail | Header | Back to Incidents Button | Button (`<Link>`) | Navigates back to `/incidents` table | None | None | Browser Click | Navigates to `/incidents` | PASS |
| Incident Detail | Header | Run AI Investigation Button | Primary Button | Triggers multi-agent workflow on incident | `can_request` / Analyzer | `POST /incidents/:id/analyze` | Browser Click | Executes workflow without timeout | PASS |
| Incident Detail | Header | Create Approval Request Button | Secondary Button | Generates plan and opens approval request | `can_request` | `POST /incidents/:id/approvals` | Browser Click | Creates approval record | PASS |
| Incident Detail | Tabs Bar | Overview Tab | Tab Button | Shows incident metadata and summary cards | None | `GET /incidents/:id` | Browser Click | Displays overview content | PASS |
| Incident Detail | Tabs Bar | Investigation Tab | Tab Button | Shows AI investigation findings and evidence | None | Query Cache / API | Browser Click | Displays investigation findings | PASS |
| Incident Detail | Tabs Bar | Remediation Tab | Tab Button | Shows generated remediation plan actions | None | Approval Snapshot | Browser Click | Displays remediation plan | PASS |
| Incident Detail | Tabs Bar | Approvals Tab | Tab Button | Shows approval history and decision events | None | `GET /approvals?incident_id=` | Browser Click | Displays approval records table | PASS |
| Incident Detail | Tabs Bar | Executions Tab | Tab Button | Shows linked execution runs | None | `GET /executions?incident_id=` | Browser Click | Displays executions table | PASS |
| Incident Detail | Tabs Bar | Verifications Tab | Tab Button | Shows post-execution verifications | None | `GET /verifications?incident_id=` | Browser Click | Displays verifications table | PASS |
| Incident Detail | Tabs Bar | Rollbacks Tab | Tab Button | Shows rollback assessments | None | `GET /rollback-assessments?incident_id=` | Browser Click | Displays rollback assessments table | PASS |

---

## 5. Page 4 — Investigation and RCA (`/investigations`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Investigation | Header | Incident Selector Dropdown | Select (`<Select>`) | Selects incident to view/run investigation | None | `GET /incidents` | Select Option | Loads selected incident context | PASS |
| Investigation | Top Card | Execute AI Investigation Button | Primary Button | Runs LangGraph workflow (triage->evidence->rca) | `can_request` / Analyzer | `POST /incidents/:id/analyze` | Browser Click | Runs workflow, renders telemetry & RCA | PASS |
| Investigation | Evidence Card | Observed Evidence Grid | Metrics Cards | Displays triage priority, snapshot timestamp, human review flag | None | Cached Analysis | Visual Inspection | Displays verified deterministic metrics | PASS |
| Investigation | Evidence Card | Raw Prometheus Metrics Grid | Grid of Metrics | Displays `cpu_percent`, `latency_seconds`, `error_rate`, `service_up` | None | Cached Analysis | Visual Inspection | Accurate Prometheus readings rendered | PASS |
| Investigation | Observations Card | Agentic Observations View | Structured Card | Displays confidence tier, key telemetry observations, diagnostic checks | None | Cached Analysis | Visual Inspection | Observations displayed accurately | PASS |
| Investigation | RCA Matrix | Hypotheses Matrix View | Interactive Grid | Displays most likely hypothesis and evidence matrix | None | Cached Analysis | Visual Inspection | Supporting, contradicting, missing evidence rendered | PASS |
| Investigation | RCA Matrix | Root Cause Confirmed Flag | Safety Badge | Enforces `Root Cause Confirmed: False` | None | Cached Analysis | Visual Inspection | Mandatory false displayed | PASS |

---

## 6. Page 5 — Remediation Plans (`/remediation`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Remediation | Header | Plan Selector Dropdown | Select (`<select>`) | Switches between available approval plans | None | `GET /approvals` | Select Option | Displays selected plan version | PASS |
| Remediation | Plan Header | Inspect Decision & Audit Link | Secondary Button (`<Link>`) | Navigates to `/approvals` | None | None | Browser Click | Navigates to `/approvals` | PASS |
| Remediation | Plan Header | Execution Sandbox Link | Primary Button (`<Link>`) | Navigates to `/executions` | None | None | Browser Click | Navigates to `/executions` | PASS |
| Remediation | Safety Info | Guardrail Enforcement Indicators | Badge Display | Confirms Execution Enabled = False, Human Approval Required = True | None | None | Visual Inspection | Badges show strict guardrail bounds | PASS |
| Remediation | Actions List | Recommended Action Cards | Card List | Displays action description, parameters, risk tier, rollback considerations | None | Plan Snapshot | Visual Inspection | All actions advisory with risk details | PASS |

---

## 7. Page 6 — Human Approval Gateway (`/approvals`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Approvals | Filter Bar | Status Filter Buttons | Button Group | Filters table by `all`, `pending`, `approved`, `rejected`, `revision_requested`, `expired`, `superseded` | None | Client-side filter | Click Tab | Table filters to selected status | PASS |
| Approvals | Table | View Details Action Button | Ghost Button | Opens approval details modal | None | `GET /approvals/:id` | Browser Click | Modal opens with plan snapshot | PASS |
| Approvals | Table | Quick Approve Button | Success Button | Opens decision modal with `approve` mode | `can_approve` & not requester | None | Browser Click | Opens decision modal | PASS |
| Approvals | Table | Quick Reject Button | Danger Button | Opens decision modal with `reject` mode | `can_approve` | None | Browser Click | Opens decision modal | PASS |
| Approvals | Table | Quick Request Revision Button | Warning Button | Opens decision modal with `revision` mode | `can_approve` | None | Browser Click | Opens decision modal | PASS |
| Approvals | Decision Modal | Reason / Comment Input | Form Input / Textarea | Captures decision rationale; mandatory for reject & revision | `can_approve` | None | Type comment | Validates non-empty on reject/revision | PASS |
| Approvals | Decision Modal | Confirm Decision Button | Action Button | Submits approval, rejection, or revision request | `can_approve` | `POST /approvals/:id/approve` (or reject/revision) | Click Confirm | Decision persisted, status updated | PASS |
| Approvals | Decision Modal | Cancel Modal Button | Ghost Button | Closes modal without recording decision | None | None | Click Cancel | Modal closes cleanly | PASS |

---

## 8. Page 7 — Execution Interface (`/executions`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Executions | Header | Simulate Execution Button | Secondary Button | Opens Simulate Execution modal dialog | `can_execute` | `GET /approvals?status=approved` | Browser Click | Modal opens | PASS |
| Executions | Header | Run Live Diagnostic Button | Primary Button | Opens Live Read-Only Diagnostic modal dialog | `can_execute` & Live Enabled | `GET /execution-operations` | Browser Click | Modal opens with warning gates | PASS |
| Executions | Registry | Operation Registry Cards | Card Grid | Lists allowlisted diagnostic operations | None | `GET /execution-operations` | Visual Inspection | Only allowlisted operations displayed | PASS |
| Executions | Simulate Modal | Approved Plan Dropdown | Select (`<Select>`) | Selects approved plan to execute | `can_execute` | `GET /approvals` | Select Option | Selection updates | PASS |
| Executions | Simulate Modal | Operation Selector | Select (`<Select>`) | Selects allowlisted operation | `can_execute` | None | Select Option | Selection updates | PASS |
| Executions | Simulate Modal | Recommendation Index Input | Number Input | Specifies action index from approved plan | `can_execute` | None | Type Number | Index updates | PASS |
| Executions | Simulate Modal | Submit Simulation Button | Primary Button | Submits simulation execution request | `can_execute` | `POST /executions/simulate` | Form Submit | Simulation runs, detail modal opens | PASS |
| Executions | Simulate Modal | Cancel Button | Ghost Button | Closes simulate modal | None | None | Browser Click | Modal closes cleanly | PASS |
| Executions | Live Modal | Acknowledgment Checkbox | Form Checkbox | Mandatory confirmation of read-only scope | `can_execute` | None | Check Box | Enables Submit button | PASS |
| Executions | Live Modal | Submit Diagnostic Button | Danger/Action Button | Submits live diagnostic request | `can_execute` | `POST /executions/diagnose` | Form Submit | Validates gates, records audit | PASS |
| Executions | Table | Inspect Action Buttons | Secondary Button | Opens execution detail modal | None | `GET /executions/:id` | Browser Click | Modal displays full execution record | PASS |

---

## 9. Page 8 — Post-Execution Verification (`/verifications`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Verifications | Header | Create Verification Button | Primary Button | Opens verification creation modal | `can_verify` | `GET /executions` | Browser Click | Modal opens | PASS |
| Verifications | Table | Inspect Action Buttons | Secondary Button | Opens verification detail modal | None | `GET /verifications/:id` | Browser Click | Displays statistical diff modal | PASS |
| Verifications | Create Modal | Execution Selector Dropdown | Select (`<Select>`) | Selects execution run to verify | `can_verify` | None | Select Option | Target execution selected | PASS |
| Verifications | Create Modal | Baseline Window Input | Number Input | Sets pre-execution sample window (minutes) | `can_verify` | None | Type Number | Value updates | PASS |
| Verifications | Create Modal | Follow-up Window Input | Number Input | Sets post-execution sample window (minutes) | `can_verify` | None | Type Number | Value updates | PASS |
| Verifications | Create Modal | Min Samples Input | Number Input | Sets required sample count threshold | `can_verify` | None | Type Number | Value updates | PASS |
| Verifications | Create Modal | Submit Verification Button | Primary Button | Evaluates statistical telemetry delta | `can_verify` | `POST /executions/:id/verifications` | Form Submit | Verification created, modal opens | PASS |
| Verifications | Create Modal | Cancel Button | Ghost Button | Closes creation modal | None | None | Browser Click | Modal closes cleanly | PASS |

---

## 10. Page 9 — Rollback Readiness (`/rollbacks`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Rollbacks | Header | Assess Rollback Readiness Button | Primary Button | Opens rollback assessment modal | `can_assess_rollback` | `GET /executions` | Browser Click | Modal opens | PASS |
| Rollbacks | Table | Inspect Action Buttons | Secondary Button | Opens rollback detail modal | None | `GET /rollback-assessments/:id` | Browser Click | Displays reversibility analysis | PASS |
| Rollbacks | Create Modal | Execution Target Selector | Select (`<Select>`) | Selects execution to evaluate | `can_assess_rollback` | None | Select Option | Selection updates | PASS |
| Rollbacks | Create Modal | Submit Assessment Button | Primary Button | Computes pre-flight reversibility evaluation | `can_assess_rollback` | `POST /executions/:id/rollback-assessments` | Form Submit | Assessment created, detail opens | PASS |
| Rollbacks | Create Modal | Cancel Button | Ghost Button | Closes assessment modal | None | None | Browser Click | Modal closes cleanly | PASS |

---

## 11. Page 10 — Audit History (`/audit`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Audit History | Header | Category Filter Tabs | Button Group | Filters by `all`, `approval`, `execution`, `verification`, `rollback` | None | `GET /audit/events?category=` | Click Tab | List updates to category | PASS |
| Audit History | Filter Bar | Search Input Field | Text Input (`<input>`) | Filters events by event_type, actor, or resource UUID | None | Client-side filter | Type query | Live-filters table rows | PASS |
| Audit History | Table | View Event Details Button | Ghost Button | Opens audit event payload modal | None | Direct Event Payload | Browser Click | Modal displays structured JSON payload | PASS |
| Audit History | Modal | Close Modal Button | Ghost Button | Closes event details modal | None | None | Click Close | Modal closes cleanly | PASS |

---

## 12. Page 11 — Settings (`/settings`)

| Page / Area | Component | Control Name | Control Type | Expected Behaviour | Required Permission | Related API Endpoint | Test Method | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Settings | Card 2 | Grafana External Link | External Link (`<a>`) | Opens Grafana UI (`:3000`) in new tab | None | Direct Link | Browser Click | Opens Grafana in new tab | PASS |
| Settings | Card 4 | Permission Matrix Display | Status Icons Grid | Shows active privileges for current persona | None | `GET /overview/settings` | Visual Inspection | Accurate green checkmarks / red crosses | PASS |
| Settings | Card 1-3 | Runtime Settings Cards | Static Cards | Displays environment, version, proxy scope, guardrail flags | None | `GET /overview/settings` | Visual Inspection | Accurate non-sensitive settings rendered | PASS |

---
**Summary of Controls Discovered:** 62 primary functional controls cataloged across 11 routes and global layouts.
