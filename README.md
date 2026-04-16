# MCP Enterprise (Production Baseline)

This project is now a production-style MCP service with:

- API key middleware on HTTP transport
- Structured JSON logs + audit logs per tool call
- Request IDs and trace IDs
- Redis read-cache for read tools/resources
- PostgreSQL persistence (no in-memory demo store)
- Per-tool Prometheus metrics
- Rate limiting
- RBAC + tenant isolation
- CI pipeline (Ruff + pytest + Docker build)
- Staging and production environment separation

## Architecture

- Transport: FastMCP (`/mcp`) over streamable HTTP
- Security boundary: `RequestSecurityMiddleware`
- Data: SQLAlchemy + PostgreSQL
- Cache + rate limiter backend: Redis (memory fallback if unavailable)
- Observability:
  - logs to stderr in JSON
  - audit logger emits `event=tool_call`
  - Prometheus metrics at `/metrics`

## Enterprise Portal

Two separated surfaces are provided:

1. Customer surface: `http://localhost:8080/portal/chat`
   - clean chat-only UI
   - GDPR/compliance notice
   - persistent conversation memory per session
   - no customer-side approval controls

2. Admin/staff surface: `http://localhost:8080/portal/admin`
   - role assignment for agent behavior per tenant
   - pending approval queue for write operations
   - approve/reject controls
   - observability summary (metrics, DB rows, Redis keys, tool audit events)

Admin API calls require:

- `x-api-key`
- `x-admin-api-key`
- `x-role: admin`
- `x-tenant-id`

## Step-by-Step Training Path

### Interactive Day-1 Lab UI

Open `http://localhost:8080/trainer` after startup.

What this gives you:

- Chat panel that calls a real model with MCP tools.
- Live Prometheus counters/histograms focused on MCP behavior.
- Live PostgreSQL snapshots (`orders`, `refund_requests`).
- Live Redis cache key inspection.
- Optional runtime OpenAI key input in the UI (stored in browser session only).

Training flow:

1. Use role `viewer` and run a refund prompt to observe RBAC denial.
2. Switch to `support_manager` and run refund again to observe success.
3. Watch:
   - `mcp_tool_calls_total` status labels change (`forbidden` vs `success`)
   - cache keys appear/disappear
   - refund rows inserted in PostgreSQL

If model chat fails:

1. Set `OPENAI_API_KEY` in server env, or
2. Paste a valid API key into the UI runtime key field.

### Step 1: Run local stack (real infra)

```bash
docker compose up --build
```

Services:

- MCP HTTP server: `http://localhost:8080/mcp`
- Health: `http://localhost:8080/healthz`
- Metrics: `http://localhost:8080/metrics`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### Step 2: Understand request security

All non-public endpoints require:

- `x-api-key`
- `x-tenant-id` (tenant isolation)
- `x-role` (RBAC)

Every response includes:

- `x-request-id`
- `x-trace-id`

### Step 3: Understand RBAC decisions

- Read tools: roles in `RBAC_READ_ROLES`
- Write tools: roles in `RBAC_WRITE_ROLES`
- Enforced in `security/rbac.py` and invoked by every tool execution.

### Step 4: Understand persistence and tenancy

Orders/refunds are persisted in PostgreSQL and scoped by `tenant_id`.
All queries in `domain/orders.py` are tenant-scoped.

### Step 5: Understand cache and invalidation

- `get_order_status_tool` and return policy use Redis cache.
- Refund creation invalidates order status cache key.

### Step 6: Understand observability

- Tool calls record:
  - latency histogram
  - outcome counter
  - structured audit event
- HTTP traffic records request count + latency.

### Step 7: CI quality gate

GitHub Actions workflow runs:

1. `ruff check .`
2. `pytest -q`
3. `docker build`

### Step 8: Environment promotion model

Templates:

- `.env.example` (dev)
- `.env.staging.example`
- `.env.prod.example`

Compose overlays:

- `docker-compose.staging.yml`
- `docker-compose.prod.yml`

Example:

```bash
# staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml up --build

# prod
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

## Suggested Engineering Progression

1. Add Alembic migrations (replace `create_all` bootstrap).
2. Move API keys to secret manager and enable key rotation schedule.
3. Replace API keys with OAuth/JWT verifier for user-level identity.
4. Emit OpenTelemetry traces and export to your APM.
5. Add load tests for rate limit and cache hit ratio.

## Local Quality Commands

```bash
ruff check .
pytest -q
docker build -t mcp-enterprise:local .
```
