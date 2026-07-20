import json
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import Pax8Client, Pax8Error

_NO_TOKEN = "Error: No Pax8 token configured. Set PAX8_API_TOKEN or use AUTH_MODE=gateway."


def register(mcp: FastMCP, client_factory: Callable[[], Pax8Client | None]) -> None:
    @mcp.tool()
    async def pax8_list_invoices(
        page: int = 0,
        size: int = 10,
        sort: str | None = None,
        company_id: str | None = None,
        status: str | None = None,
    ) -> str:
        """List invoices in the Pax8 partner account.

        Args:
            page: Zero-based page number for pagination (default: 0).
            size: Number of results per page (default: 10).
            sort: Sort field and direction, e.g. "invoiceDate,desc".
            company_id: Filter by company ID.
            status: Filter by invoice status, e.g. "Paid", "Unpaid", "Overdue".
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.get(
                "/invoices",
                params={
                    "page": page,
                    "size": size,
                    "sort": sort,
                    "companyId": company_id,
                    "status": status,
                },
            )
            return json.dumps(result, indent=2)
        except Pax8Error as e:
            return f"Error {e.status_code}: {e.message}"

    @mcp.tool()
    async def pax8_list_invoice_items(
        invoice_id: str,
        page: int = 0,
        size: int = 10,
    ) -> str:
        """List line items for a specific invoice.

        Args:
            invoice_id: The unique identifier of the invoice.
            page: Zero-based page number for pagination (default: 0).
            size: Number of results per page (default: 10).
        """
        client = client_factory()
        if client is None:
            return _NO_TOKEN
        try:
            result = await client.get(
                f"/invoices/{invoice_id}/items",
                params={"page": page, "size": size},
            )
            return json.dumps(result, indent=2)
        except Pax8Error as e:
            return f"Error {e.status_code}: {e.message}"
