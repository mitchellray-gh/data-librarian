"""Thin async-friendly wrapper around the Databricks SDK.

When credentials are missing the wrapper returns a synthetic "demo" schema
so the rest of the app — agent, UI, chat — still runs end-to-end. Replace
the configured workspace + catalog/schema in `.env` to point it at real data.
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable

from .config import settings


# ---------- demo fallback used when Databricks is unconfigured ----------
_DEMO_TABLES: list[dict[str, Any]] = [
    {
        "name": "customers",
        "comment": "Master customer dimension",
        "columns": [
            {"name": "customer_id", "type": "BIGINT"},
            {"name": "email", "type": "STRING"},
            {"name": "country", "type": "STRING"},
            {"name": "created_at", "type": "TIMESTAMP"},
        ],
    },
    {
        "name": "orders",
        "comment": "Order fact table",
        "columns": [
            {"name": "order_id", "type": "BIGINT"},
            {"name": "customer_id", "type": "BIGINT"},
            {"name": "amount_usd", "type": "DECIMAL(18,2)"},
            {"name": "ordered_at", "type": "TIMESTAMP"},
            {"name": "status", "type": "STRING"},
        ],
    },
    {
        "name": "products",
        "comment": "Product catalog",
        "columns": [
            {"name": "product_id", "type": "BIGINT"},
            {"name": "sku", "type": "STRING"},
            {"name": "category", "type": "STRING"},
            {"name": "price_usd", "type": "DECIMAL(18,2)"},
        ],
    },
]


class DatabricksClient:
    def __init__(self) -> None:
        self._workspace = None
        self._sql = None
        if settings.databricks_configured:
            try:
                from databricks.sdk import WorkspaceClient  # type: ignore

                self._workspace = WorkspaceClient(
                    host=settings.databricks_host,
                    token=settings.databricks_token,
                )
            except Exception:  # noqa: BLE001 — degrade gracefully
                self._workspace = None

    @property
    def configured(self) -> bool:
        return self._workspace is not None

    # ---------- catalog walking ----------
    async def list_tables(self) -> list[dict[str, Any]]:
        """Return list of {name, comment, columns:[{name,type}]} for the configured schema."""
        if not self.configured:
            return list(_DEMO_TABLES)

        def _work() -> list[dict[str, Any]]:
            assert self._workspace is not None
            out: list[dict[str, Any]] = []
            try:
                tables: Iterable[Any] = self._workspace.tables.list(
                    catalog_name=settings.databricks_catalog,
                    schema_name=settings.databricks_schema,
                )
            except Exception:  # noqa: BLE001
                return out
            for t in tables:
                cols = []
                for c in (getattr(t, "columns", None) or []):
                    cols.append({
                        "name": getattr(c, "name", ""),
                        "type": getattr(c, "type_text", "") or str(getattr(c, "type_name", "")),
                        "comment": getattr(c, "comment", "") or "",
                    })
                out.append({
                    "name": getattr(t, "name", ""),
                    "comment": getattr(t, "comment", "") or "",
                    "columns": cols,
                })
            return out

        return await asyncio.to_thread(_work)

    async def sample_rows(self, table_name: str, limit: int) -> list[dict[str, Any]]:
        """Best-effort sampling. Returns [] if unavailable.

        Real implementations should use Databricks SQL via a configured warehouse;
        we keep this conservative because warehouse selection is deployment-specific.
        """
        if limit <= 0:
            return []
        if not self.configured:
            # synthetic samples consistent with the demo schema
            if table_name == "customers":
                return [{"country": "US"}, {"country": "US"}, {"country": "DE"}]
            if table_name == "orders":
                return [{"status": "PAID"}, {"status": "PAID"}, {"status": "REFUNDED"}]
            return []
        # No SQL warehouse wired up by default — return empty so the agent
        # still produces metadata-driven inferences without failing.
        return []


client = DatabricksClient()
