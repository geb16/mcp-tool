# MCP Enterprise

Production-style Python MCP service that demonstrates secure tool execution, approval workflows, tenant isolation, and observability with real infrastructure (PostgreSQL + Redis + Prometheus metrics).

## Scope

This repository provides:

- MCP tools and resources over stdio and HTTP transports.
- API-key authentication middleware for HTTP requests.
- RBAC for read/write tool access.
- Tenant isolation at middleware and data-query levels.
- Human approval workflow for sensitive write actions.
- Structured JSON logs with request and trace correlation.
- Tool audit events and per-tool metrics.
- Redis cache for read tools/resources.
- PostgreSQL persistence for domain and portal workflows.
- Development trainer UI and enterprise portal (customer + admin).

## Architecture

### Runtime Components

- `FastMCP` server and tool registration: `src/enterprise_mcp/mcp/common.py`
- HTTP application and route wiring: `src/enterprise_mcp/mcp/http_server.py`
- Security middleware (auth, role validation, rate limiting, request IDs): `src/enterprise_mcp/security/middleware.py`
- Domain logic (orders/refunds): `src/enterprise_mcp/domain/orders.py`
- Data access and models (SQLAlchemy): `src/enterprise_mcp/data/db.py`
- Cache and rate-limit backend (Redis + fallback): `src/enterprise_mcp/data/cache.py`, `src/enterprise_mcp/security/rate_limit.py`
- Observability (metrics, structured audit, context): `src/enterprise_mcp/observability/*`
- Customer/Admin portal workflow: `src/enterprise_mcp/portal/*`
- Trainer lab workflow: `src/enterprise_mcp/trainer/*`

### Request Flow (HTTP `/mcp`)

1. `build_http_app()` builds the Starlette app and adds `RequestSecurityMiddleware`.
2. Middleware sets `request_id`/`trace_id`, authenticates headers, validates role/tenant, applies rate limits.
3. MCP tool entry calls `_execute_tool()` in `mcp/common.py`.
4. `_execute_tool()` enforces RBAC via `ensure_tool_access()`.
5. Tool executes domain logic, with Redis read-cache where applicable.
6. Tool emits metrics and structured audit event.
7. Middleware appends `x-request-id` and `x-trace-id` response headers.

## Repository Map

### Entrypoints

- `main.py`: stdio runtime entrypoint (logging + DB init + MCP run).
- `src/enterprise_mcp/mcp/stdio_server.py`: alternate stdio launch entrypoint.
- `src/enterprise_mcp/mcp/http_server.py`: HTTP app factory and local server startup.

### Configuration and Models

- `src/enterprise_mcp/config.py`: environment configuration and derived settings.
- `src/enterprise_mcp/models.py`: Pydantic request models for domain/tool contracts.
- `src/enterprise_mcp/approval.py`: read-only/dangerous tool classification helpers.

### Data Layer

- `src/enterprise_mcp/data/db.py`: SQLAlchemy models, session scope, DB bootstrap/seed.
- `src/enterprise_mcp/data/cache.py`: Redis JSON cache wrapper with safe fallback.

### Domain Layer

- `src/enterprise_mcp/domain/orders.py`: tenant-scoped order lookup, refund creation, policy resource data.

### MCP Layer

- `src/enterprise_mcp/mcp/common.py`: MCP tools/resources with caching, RBAC, metrics, and audit integration.
- `src/enterprise_mcp/mcp/http_server.py`: HTTP routes (`/mcp`, `/healthz`, `/metrics`, trainer, portal).

### Security Layer

- `src/enterprise_mcp/security/middleware.py`: API-key auth, tenant/role validation, rate limiting, trace headers.
- `src/enterprise_mcp/security/rbac.py`: read/write role authorization checks.
- `src/enterprise_mcp/security/rate_limit.py`: Redis/in-memory rate limiter.
- `src/enterprise_mcp/security/context.py`: current tenant/role helpers from request context.

### Observability Layer

- `src/enterprise_mcp/logging.py`: JSON logging formatter with request context fields.
- `src/enterprise_mcp/observability/context.py`: context variables (`request_id`, `trace_id`, `tenant_id`, `role`, `principal`).
- `src/enterprise_mcp/observability/metrics.py`: Prometheus counters/histograms and helpers.
- `src/enterprise_mcp/observability/audit.py`: per-tool audit event emission.
- `src/enterprise_mcp/observability/events.py`: in-memory event buffer for admin/trainer views.

### UIs and APIs

- `src/enterprise_mcp/trainer/*`: dev/test learning interface + APIs.
- `src/enterprise_mcp/portal/*`: customer/admin portal UIs, APIs, and approval orchestration.

### Tests

- `tests/conftest.py`: isolated test environment and DB reset fixture.
- `tests/test_http_security.py`: middleware auth/tracing coverage.
- `tests/test_orders.py`: domain behavior coverage.
- `tests/test_rbac.py`: RBAC write-block coverage.
- `tests/test_tenant_isolation.py`: tenant data isolation coverage.
- `tests/test_tool_smoke.py`: MCP smoke coverage.
- `tests/test_trainer_ui.py`: trainer endpoint coverage.
- `tests/test_portal.py`: portal API and approval workflow coverage.

## Environment Model

### Files

- `.env.example`
- `.env.staging.example`
- `.env.prod.example`

### Compose Overlays

- `docker-compose.yml` (base/dev)
- `docker-compose.staging.yml`
- `docker-compose.prod.yml`

### Core Variables

- `APP_ENV` = `dev | test | staging | prod`
- `MCP_API_KEY` or `MCP_API_KEYS`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `REQUIRE_TENANT_HEADER`
- `RBAC_READ_ROLES`
- `RBAC_WRITE_ROLES`

## Local Run

```bash
docker compose up --build
```

Endpoints:

- MCP HTTP: `http://localhost:8080/mcp`
- Health: `http://localhost:8080/healthz`
- Metrics: `http://localhost:8080/metrics`
- Trainer UI: `http://localhost:8080/trainer` (dev/test only)
- Customer Portal UI: `http://localhost:8080/portal/chat`
- Admin Portal UI: `http://localhost:8080/portal/admin`

## API Contracts

### Common Headers (Protected Endpoints)

- `x-api-key: <api key>`
- `x-tenant-id: <tenant id>` (if required by config)
- `x-role: <viewer|support_agent|support_manager|admin>`

### Response Correlation Headers

- `x-request-id`
- `x-trace-id`

### Portal Admin Headers

- `x-admin-api-key: <api key>`
- `x-api-key: <api key>`
- `x-role: admin`
- `x-tenant-id: <tenant>`

## Security Behavior

- Invalid API key: `401`
- Missing required tenant header: `400`
- Unknown role: `403`
- Rate limit exceeded: `429`
- In `staging/prod`, no configured API keys is treated as server misconfiguration (`500`).

## Data and Consistency Rules

- All domain reads/writes are tenant-scoped.
- Refund creation requires:
  - existing order
  - refundable order
  - explicit human approval flag
- Successful refund creation sets `order.refundable = False`.
- Successful refund creation invalidates order-status cache key.

## Observability

### Metrics

- `mcp_http_requests_total`
- `mcp_http_request_latency_seconds`
- `mcp_tool_calls_total`
- `mcp_tool_call_latency_seconds`
- `mcp_cache_events_total`
- `mcp_rate_limit_events_total`

### Logging

- JSON logs to stderr with:
  - timestamp, level, logger, message, `app_env`
  - `request_id`, `trace_id`, `tenant_id`, `role`, `principal`

### Audit Events

- One structured event per tool execution:
  - tool name, status, duration, arguments, outcome, request/trace/tenant/role context.

## Quality and CI

Local commands:

```bash
ruff check .
pytest -q
docker build -t mcp-enterprise:local .
```

CI pipeline includes:

1. Ruff checks
2. Pytest suite
3. Docker build validation

## Acknowledgment

This implementation is built around the Model Context Protocol (MCP) ecosystem and uses FastMCP, Starlette, SQLAlchemy, Redis, and Prometheus client libraries.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Feature Status (Current Build)

- API key auth middleware: implemented
- Structured tool-call audit logs: implemented
- Request ID and trace ID propagation: implemented
- Redis cache for read paths: implemented
- PostgreSQL persistence: implemented
- Per-tool metrics: implemented
- Rate limiting: implemented
- RBAC + tenant isolation: implemented
- CI checks (Ruff + pytest + Docker build): implemented
- Staging/prod environment overlays: implemented
- Customer/admin split portal with approval queue: implemented
