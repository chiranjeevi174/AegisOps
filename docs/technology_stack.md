# AegisOps — Technology Stack & Engineering Ecosystem

This document details the complete technology stack used across the **AegisOps** platform, specifying the purpose, architectural layer, and engineering justification for each component.

---

## 1. Backend Core & Agentic AI Layer

| Technology | Version / Spec | Purpose in AegisOps | Architectural Rationale |
|---|---|---|---|
| **Python** | 3.12 | Primary backend runtime | Modern typed syntax, native `asyncio`, exception groups, and high-performance package ecosystem. |
| **FastAPI** | 0.115+ | Asynchronous REST API framework | High-throughput asynchronous request handling, OpenAPI auto-documentation, and dependency-injected security/RBAC. |
| **LangGraph** | 0.2+ | Agentic workflow state graph orchestration | Manages deterministic state machine transitions between Triage, Evidence Collection, Gemini Investigation, RCA, and Planning. |
| **Google Gemini** | `gemini-3.5-flash-lite` | Generative AI reasoning & synthesis engine | High-speed, context-window-rich multi-signal correlation and root cause hypothesis synthesis with structured JSON output. |
| **PostgreSQL** | 17 (Alpine) | Persistent relational datastore | ACID compliance, JSONB support for immutable plan snapshots, robust relational constraints, and audit logging. |
| **SQLAlchemy** | 2.0+ (Async) | Asynchronous Object-Relational Mapping (ORM) | Clean typed models, async connection pooling, and resilient transaction management via `asyncpg`. |
| **Alembic** | 1.14+ | Database schema migration engine | Version-controlled, reproducible schema migrations tracked up to migration head `2b6feb4eb4be`. |
| **Pydantic** | v2 | Data validation & settings management | Strict schema enforcement, compile-time/runtime type validation, and robust `.env` parsing. |

---

## 2. Observability & Telemetry Infrastructure

| Technology | Version / Spec | Purpose in AegisOps | Architectural Rationale |
|---|---|---|---|
| **Prometheus** | v3.5.0 | Telemetry collection & timeseries engine | Pull-based metrics scraping, multi-dimensional PromQL evaluation, and automated alert triggering for SLA violations. |
| **Alertmanager** | v0.28.1 | Alert deduplication & webhook dispatch | Deduplicates firing threshold alerts, suppresses flapping signals, and dispatches authenticated webhooks with bearer tokens. |
| **Grafana** | v12.1.1 | Platform telemetry & operations dashboard | Auto-provisioned dashboards visualizing golden signals (CPU, latency, error rates), incident volume, and agent runtimes. |

---

## 3. Frontend & User Interface

| Technology | Version / Spec | Purpose in AegisOps | Architectural Rationale |
|---|---|---|---|
| **React** | 18.3 | User interface component library | Component-driven declarative UI, virtual DOM diffing, and strict state lifecycle hooks. |
| **TypeScript** | 5.6 | Statically typed frontend language | Compile-time type safety across API schemas, domain models, and React props, eliminating null pointer defects. |
| **Vite** | 6.0 | Modern build tool & development server | Lightning-fast Hot Module Replacement (HMR), optimized Rollup production bundling, and route-level code splitting. |
| **Tailwind CSS** | 3.4 | Utility-first CSS styling system | Cohesive dark-mode UI design, glassmorphism aesthetics, responsive layouts, and zero runtime CSS overhead. |
| **TanStack React Query** | v5 | Client-side data synchronization & caching | Automated background polling, server state caching, and optimistic UI updates for real-time incident tracking. |
| **Lucide React** | 0.468+ | Iconography library | Consistent, lightweight SVG icons representing operational statuses, incident severities, and safety gates. |
| **Recharts** | 2.15 | Operational metrics visualization | Smooth, responsive SVG charts displaying real-time telemetry curves, resource utilization, and error spikes. |

---

## 4. Containerization & Deployment Layer

| Technology | Version / Spec | Purpose in AegisOps | Architectural Rationale |
|---|---|---|---|
| **Docker** | Engine 28+ | Multi-stage containerization engine | Consistent runtime environments across backend, frontend, database, and telemetry services. |
| **Docker Compose** | v2 | Multi-container stack orchestration | Defines isolated networks, service dependencies, health checks, named persistent volumes, and loopback bindings. |
| **Nginx** | 1.27 (Alpine) | Production web server & reverse proxy | Serves static React SPA assets, applies HTTP security headers (`nosniff`, `DENY`, `no-store`), and proxies API calls. |

---

## 5. Development, Linting & Testing Tooling

| Technology | Version / Spec | Purpose in AegisOps | Architectural Rationale |
|---|---|---|---|
| **uv** | 0.5+ | High-speed Python package & project manager | Replaces pip, virtualenv, and poetry with sub-second dependency resolution and reproducible locking via `uv.lock`. |
| **Pytest** | 8.3+ | Backend automated testing framework | Executes 245 regression tests covering unit, API, database, security, and agent workflow assertions. |
| **Vitest** | 2.1+ | Frontend testing runner | Vite-native unit and component test runner executing 15 comprehensive UI tests in jsdom. |
| **Ruff** | 0.8+ | High-speed Python linter and formatter | Enforces PEP 8 compliance, import sorting, and code cleanliness in milliseconds across all Python source trees. |
| **Pyright** | Latest | Static type checker for Python | Enforces strict type checking across source and evaluation modules with zero errors. |
| **ESLint** | 9.17 | TypeScript & React code linter | Detects anti-patterns, hook dependency bugs, and syntax inconsistencies across frontend code. |
