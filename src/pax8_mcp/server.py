import contextvars
import sys
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import Pax8Client
from .config import Settings

# ─────────────────────────────────────────────────────────────────────────────
# Per-request token contextvar for gateway mode.
# GatewayTokenMiddleware sets this before the MCP handler runs.
# Python asyncio copies context per task, so concurrent requests are isolated.
# ─────────────────────────────────────────────────────────────────────────────
_gateway_token_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pax8_gateway_token", default=None
)


def get_client_from_context(settings: Settings) -> Pax8Client | None:
    """Resolve the active Pax8Client for the current request context."""
    if settings.auth_mode == "gateway":
        token = _gateway_token_var.get()
    else:
        token = settings.pax8_api_token

    if not token:
        return None
    return Pax8Client(token, settings.pax8_base_url, settings.pax8_auth_header)


class GatewayTokenMiddleware:
    """ASGI middleware for gateway mode.

    Reads the configured auth header from each request and stores the token in
    the contextvar for the duration of that request. Returns 401 if the header
    is missing on /mcp requests.
    """

    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        # Header lookup is case-insensitive in Starlette
        token = request.headers.get(self.settings.pax8_auth_header.lower())
        if not token:
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": (
                        f"Gateway mode requires the {self.settings.pax8_auth_header} header"
                    ),
                    "required_headers": [self.settings.pax8_auth_header],
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        ctx_token = _gateway_token_var.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            _gateway_token_var.reset(ctx_token)


def create_mcp_server(settings: Settings) -> FastMCP:
    """Build the FastMCP server instance and register all tools."""
    # DNS-rebinding protection is disabled because the container runs behind
    # mcp-gateway on an internal Docker network and is never publicly exposed.
    mcp = FastMCP(
        name="pax8-mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    client_factory: Callable[[], Pax8Client | None] = lambda: get_client_from_context(settings)

    if not settings.has_credentials:
        # Graceful degradation: register only a diagnostic tool when no credentials are available.
        @mcp.tool()
        async def pax8_test_connection() -> str:
            """Test Pax8 API connection. Shows configuration requirements when credentials are missing."""
            return (
                "Error: Missing Pax8 credentials.\n\n"
                "Set the required environment variable:\n"
                "  PAX8_API_TOKEN=your_access_token_here\n\n"
                "Or use gateway mode (per-request token):\n"
                f"  AUTH_MODE=gateway\n"
                f"  Send header: {settings.pax8_auth_header}: your_access_token_here"
            )

        print(
            "Warning: No Pax8 credentials found. Only the diagnostic tool is available.",
            file=sys.stderr,
        )
        return mcp

    # Register all tool modules.
    from .tools import companies, invoices, orders, products, subscriptions, usage

    companies.register(mcp, client_factory)
    subscriptions.register(mcp, client_factory)
    invoices.register(mcp, client_factory)
    orders.register(mcp, client_factory)
    products.register(mcp, client_factory)
    usage.register(mcp, client_factory)

    return mcp
