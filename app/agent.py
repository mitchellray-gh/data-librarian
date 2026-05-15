"""The recursive live learning agent.

Runs forever as an asyncio background task. Each pass:
  1. Lists tables in the configured Unity Catalog schema.
  2. Recurses into each table → columns → (optional) sample rows.
  3. Performs lightweight inference, modeling and pattern analysis on what it sees.
  4. Distills the findings into training tips and operator guidance.
  5. Persists the growing knowledge base.
  6. Sleeps briefly, then does it all again — forever.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import Any

from .config import settings
from .databricks_client import client as databricks
from .knowledge import KnowledgeStore, TableKnowledge

log = logging.getLogger("data_librarian.agent")


# ---------- inference helpers ----------
_KEY_HINTS = ("_id", "id", "key", "uuid", "guid")
_TIME_HINTS = ("_at", "_ts", "timestamp", "date", "time")
_MONEY_HINTS = ("amount", "price", "revenue", "cost", "usd", "eur", "gbp")


def _infer_purpose(table_name: str, columns: list[dict[str, Any]]) -> str:
    name = table_name.lower()
    col_names = {(c.get("name") or "").lower() for c in columns}
    if any(n in name for n in ("fact", "event", "log", "order", "transaction")):
        return "Fact / event table — likely high-volume, append-mostly."
    if any(n in name for n in ("dim", "customer", "product", "user", "account")):
        return "Dimension / master-data table — descriptive attributes keyed by an ID."
    if "snapshot" in name or "daily" in name:
        return "Periodic snapshot table — analyze with time-window comparisons."
    if any(c.endswith("_id") for c in col_names) and any(any(t in c for t in _TIME_HINTS) for c in col_names):
        return "Looks transactional — has IDs and timestamps."
    return "General-purpose table."


def _infer_joins(table_name: str, columns: list[dict[str, Any]], all_tables: list[str]) -> list[str]:
    joins: list[str] = []
    for col in columns:
        cname = (col.get("name") or "").lower()
        if cname.endswith("_id") and cname != "id":
            stem = cname[:-3]
            for other in all_tables:
                short = other.split(".")[-1].lower()
                if short.startswith(stem) or short.rstrip("s") == stem:
                    joins.append(f"{table_name}.{col['name']} → {other}.id")
    return joins


def _column_patterns(columns: list[dict[str, Any]]) -> dict[str, Any]:
    type_hist = Counter()
    flags = {"has_primary_key_candidate": False, "has_timestamp": False, "has_money": False}
    for c in columns:
        t = (c.get("type") or "").upper()
        type_hist[t.split("(")[0] or "UNKNOWN"] += 1
        cname = (c.get("name") or "").lower()
        if any(h in cname for h in _KEY_HINTS):
            flags["has_primary_key_candidate"] = True
        if any(h in cname for h in _TIME_HINTS) or "TIMESTAMP" in t or "DATE" in t:
            flags["has_timestamp"] = True
        if any(h in cname for h in _MONEY_HINTS) or "DECIMAL" in t:
            flags["has_money"] = True
    return {"type_histogram": dict(type_hist), **flags}


def _sample_patterns(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {}
    counts: dict[str, Counter] = {}
    for row in samples:
        for k, v in row.items():
            counts.setdefault(k, Counter())[str(v)] += 1
    return {
        col: {"top_values": ctr.most_common(3), "distinct_in_sample": len(ctr)}
        for col, ctr in counts.items()
    }


def _training_tips(table_name: str, columns: list[dict[str, Any]], patterns: dict[str, Any]) -> list[str]:
    tips: list[str] = []
    short = table_name.split(".")[-1]
    if patterns.get("has_primary_key_candidate"):
        pk = next((c["name"] for c in columns if (c["name"] or "").lower().endswith(("_id", "id", "key"))), None)
        if pk:
            tips.append(f"Use `{pk}` as the join/grouping key for `{short}`.")
    if patterns.get("has_timestamp"):
        ts = next((c["name"] for c in columns if any(h in (c["name"] or "").lower() for h in _TIME_HINTS)), None)
        if ts:
            tips.append(f"Filter `{short}` on `{ts}` for time-windowed analysis; partition pruning likely available.")
    if patterns.get("has_money"):
        amt = next((c["name"] for c in columns if any(h in (c["name"] or "").lower() for h in _MONEY_HINTS)), None)
        if amt:
            tips.append(f"`{short}.{amt}` is monetary — aggregate with SUM, watch for nulls and currency.")
    if not tips:
        tips.append(f"`{short}` has {len(columns)} columns; start with a `SELECT * LIMIT 10` to eyeball it.")
    return tips


# ---------- the agent loop ----------
class LiveAgent:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="data-librarian-agent")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()

    async def _run(self) -> None:
        log.info("Live agent starting; databricks_configured=%s", databricks.configured)
        await self.store.record_activity("boot", "Librarian booting up. Stretching neurons.")
        while not self._stopping.is_set():
            try:
                await self._one_pass()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("Pass failed: %s", exc)
                await self.store.record_activity("error", f"Pass failed: {exc}")
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=settings.learn_interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def _one_pass(self) -> None:
        target = (
            f"{settings.databricks_catalog}.{settings.databricks_schema}"
            if settings.databricks_configured
            else "demo.schema"
        )
        await self.store.record_activity("scan", f"Recursive scan starting on {target}", target)
        tables = await databricks.list_tables()
        all_full_names = [f"{target}.{t['name']}" for t in tables]

        for t in tables:
            if self._stopping.is_set():
                break
            full = f"{target}.{t['name']}"
            await self.store.record_activity("read", f"Reading columns of {full}", full)
            cols = t.get("columns") or []
            patterns = _column_patterns(cols)
            samples = await databricks.sample_rows(t["name"], settings.sample_row_limit)
            spat = _sample_patterns(samples)
            tk = TableKnowledge(
                full_name=full,
                columns=cols,
                row_estimate=t.get("row_estimate"),
                sample_patterns=spat,
                inferred_purpose=_infer_purpose(t["name"], cols),
                suggested_joins=_infer_joins(full, cols, all_full_names),
                training_tips=_training_tips(full, cols, patterns),
                last_seen=time.time(),
                visits=1,
            )
            await self.store.upsert_table(tk)
            await self.store.record_activity(
                "infer",
                f"Inferred purpose for {full}: {tk.inferred_purpose}",
                full,
            )
            # yield control so the event loop stays snappy for chat + UI
            await asyncio.sleep(0)

        # global guidance built from cross-table patterns
        if self.store.tables:
            num_facts = sum(1 for t in self.store.tables.values() if "fact" in t.inferred_purpose.lower() or "event" in t.inferred_purpose.lower())
            num_dims = sum(1 for t in self.store.tables.values() if "dimension" in t.inferred_purpose.lower())
            if num_facts and num_dims:
                await self.store.add_guidance(
                    f"Schema looks star-shaped: ~{num_facts} fact-style and ~{num_dims} dimension-style tables — "
                    "join facts to dimensions on `*_id` keys."
                )
            join_count = sum(len(t.suggested_joins) for t in self.store.tables.values())
            if join_count:
                await self.store.add_guidance(
                    f"Found {join_count} probable foreign-key relationships across the schema."
                )

        await self.store.increment_pass()
        await self.store.persist()
        await self.store.record_activity(
            "pass",
            f"Pass #{self.store.passes_completed} complete. Knowing {len(self.store.tables)} tables.",
            target,
        )
