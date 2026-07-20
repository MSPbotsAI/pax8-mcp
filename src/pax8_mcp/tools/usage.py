import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import Pax8Client, Pax8Error

_NO_TOKEN = "Error: No Pax8 token configured. Set PAX8_API_TOKEN or use AUTH_MODE=gateway."


def register(mcp: FastMCP, client_factory: Callable[[], Pax8Client | None]) -> None:
    @mcp.tool()
    async def pax8_list_usage_summary_lines(
        usage_summary_id: str,
        page: int = 0,
        size: int = 10,
    ) -> str:
        """List usage lines for a specific usage summary.

        Args:
            usage_summary_id: The unique identifier of the usage summary.
            page: Zero-based page number for pagination (default: 0).
            size: Number of results per page (default: 10).
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.get(
                f"/usage-summaries/{usage_summary_id}/usage-lines",
                params={"page": page, "size": size},
            )
            return json.dumps(result, indent=2)
        except Pax8Error as e:
            return f"Error {e.status_code}: {e.message}"
