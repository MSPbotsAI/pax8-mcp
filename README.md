# pax8-mcp

Stateless HTTP MCP service for the [Pax8 Partner API](https://devx.pax8.com/reference/findcompanies). Exposes Pax8 data as MCP tools so AI assistants can query companies, subscriptions, invoices, orders, products, and usage data.

## Architecture

- **Stateless** — no user state or credentials stored between requests
- **Per-request auth** — access token passed via `X-Pax8-Token` header on every call
- **Concurrent-safe** — Python `contextvars` isolate credentials across parallel requests
- **Transports** — HTTP (production) or stdio (development)

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /mcp` | MCP protocol entry point (JSON-RPC) |
| `GET /health` | Health check |

Default port: **8080**

## Authorization

Pass your Pax8 access token in every `/mcp` request:

```
X-Pax8-Token: <your_access_token>
```

The service forwards the token as `Authorization: Bearer <token>` to the Pax8 API. Tokens are never stored globally — each request is fully isolated.

## Tool List

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `pax8_list_companies` | List companies in the partner account | `page`, `size`, `sort`, `name` |
| `pax8_list_company_contacts` | List contacts for a company | `company_id`, `page`, `size` |
| `pax8_list_subscriptions` | List subscriptions | `page`, `size`, `sort`, `company_id`, `status`, `product_id` |
| `pax8_list_subscription_usage_summaries` | List usage summaries for a subscription | `subscription_id`, `page`, `size` |
| `pax8_list_invoices` | List invoices | `page`, `size`, `sort`, `company_id`, `status` |
| `pax8_list_invoice_items` | List line items for an invoice | `invoice_id`, `page`, `size` |
| `pax8_list_orders` | List orders | `page`, `size`, `sort`, `company_id`, `status` |
| `pax8_list_products` | List products in the Pax8 marketplace | `page`, `size`, `sort`, `vendor_name`, `product_name` |
| `pax8_list_usage_summary_lines` | List usage lines for a usage summary | `usage_summary_id`, `page`, `size` |

### Parameter Details

**Pagination** (all list tools):
- `page` — zero-based page number (default: `0`)
- `size` — results per page (default: `10`)
- `sort` — field and direction, e.g. `"name,asc"` or `"createdDate,desc"`

**`pax8_list_subscriptions` status values:**
`Active`, `Cancelled`, `PendingManual`, `PendingAutomated`, `PendingCancel`, `Terminated`, `Expired`, `Trial`

## Quick Start

### Local development (env mode)

```bash
# Copy and edit environment config
cp .env.example .env
# Set PAX8_API_TOKEN and AUTH_MODE=env in .env

# Install dependencies
uv sync

# Run the server
MCP_TRANSPORT=http AUTH_MODE=env python -m pax8_mcp
```

### Docker (gateway mode — production)

```bash
docker build -t pax8-mcp .
docker run -p 8080:8080 -e AUTH_MODE=gateway pax8-mcp
```

Or with Docker Compose:

```bash
docker compose up
```

## Test Examples

**Health check:**

```bash
curl http://localhost:8080/health
# {"status":"ok","transport":"http","auth_mode":"gateway"}
```

**List companies:**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-Pax8-Token: <your_access_token>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "pax8_list_companies",
      "arguments": {"page": 0, "size": 5}
    }
  }'
```

**List subscriptions for a company:**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-Pax8-Token: <your_access_token>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "pax8_list_subscriptions",
      "arguments": {"company_id": "<company_uuid>", "status": "Active"}
    }
  }'
```

**List invoice items:**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-Pax8-Token: <your_access_token>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "pax8_list_invoice_items",
      "arguments": {"invoice_id": "<invoice_uuid>"}
    }
  }'
```

**List usage lines for a usage summary:**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-Pax8-Token: <your_access_token>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "pax8_list_usage_summary_lines",
      "arguments": {"usage_summary_id": "<usage_summary_uuid>"}
    }
  }'
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PAX8_API_TOKEN` | — | Access token (env mode only) |
| `PAX8_BASE_URL` | `https://api.pax8.com/v1` | Pax8 API base URL |
| `PAX8_AUTH_HEADER` | `X-Pax8-Token` | MCP request header carrying the token |
| `MCP_TRANSPORT` | `stdio` | `http` for production, `stdio` for local dev |
| `MCP_HTTP_PORT` | `8080` | HTTP listen port |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP listen host |
| `AUTH_MODE` | `gateway` | `gateway` (per-request, SOP-compliant) or `env` (dev only) |
