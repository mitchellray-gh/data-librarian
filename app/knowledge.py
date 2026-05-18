"""In-memory + on-disk knowledge base built up by the live learning agent."""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque


@dataclass
class TableKnowledge:
    full_name: str
    columns: list[dict[str, Any]] = field(default_factory=list)
    row_estimate: int | None = None
    sample_patterns: dict[str, Any] = field(default_factory=dict)
    inferred_purpose: str = ""
    suggested_joins: list[str] = field(default_factory=list)
    training_tips: list[str] = field(default_factory=list)
    last_seen: float = 0.0
    visits: int = 0


class KnowledgeStore:
    """Thread-safe (asyncio) accumulating knowledge base.

    The store is intentionally append-mostly: each pass *enriches* what the
    agent already knows rather than overwriting it, so the librarian feels
    like it is genuinely growing smarter over time.
    """

    def __init__(self, persist_path: str) -> None:
        self.persist_path = persist_path
        self._lock = asyncio.Lock()
        self.tables: dict[str, TableKnowledge] = {}
        self.global_patterns: dict[str, Any] = {}
        self.guidance: list[str] = []
        # bounded ring buffer of recent activity, used to drive the "alive" UI ticker
        self.activity: Deque[dict[str, Any]] = deque(maxlen=200)
        self.started_at: float = time.time()
        self.passes_completed: int = 0
        self.last_target: str = ""
        # ---- Scientist persona state (lean evolving knowledge doc) ----
        self.scientist_doc: str = ""
        self.scientist_passes: int = 0
        self.hypotheses: list[str] = []
        self.open_questions: list[str] = []
        # ---- Analyst persona state (lean evolving business brief) ----
        self.analyst_brief: str = ""
        self.analyst_passes: int = 0
        self.business_insights: list[str] = []
        self.consumer_trends: list[dict[str, Any]] = []
        self._load()

    # ---------- persistence ----------
    def _load(self) -> None:
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as fh:
                blob = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        for name, raw in (blob.get("tables") or {}).items():
            self.tables[name] = TableKnowledge(**raw)
        self.global_patterns = blob.get("global_patterns") or {}
        self.guidance = blob.get("guidance") or []
        self.passes_completed = int(blob.get("passes_completed") or 0)
        self.scientist_doc = blob.get("scientist_doc") or ""
        self.scientist_passes = int(blob.get("scientist_passes") or 0)
        self.hypotheses = blob.get("hypotheses") or []
        self.open_questions = blob.get("open_questions") or []
        self.analyst_brief = blob.get("analyst_brief") or ""
        self.analyst_passes = int(blob.get("analyst_passes") or 0)
        self.business_insights = blob.get("business_insights") or []
        self.consumer_trends = blob.get("consumer_trends") or []

    async def persist(self) -> None:
        async with self._lock:
            os.makedirs(os.path.dirname(self.persist_path) or ".", exist_ok=True)
            blob = {
                "tables": {n: t.__dict__ for n, t in self.tables.items()},
                "global_patterns": self.global_patterns,
                "guidance": self.guidance,
                "passes_completed": self.passes_completed,
                "scientist_doc": self.scientist_doc,
                "scientist_passes": self.scientist_passes,
                "hypotheses": self.hypotheses,
                "open_questions": self.open_questions,
                "analyst_brief": self.analyst_brief,
                "analyst_passes": self.analyst_passes,
                "business_insights": self.business_insights,
                "consumer_trends": self.consumer_trends,
            }
            tmp = self.persist_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(blob, fh, indent=2, default=str)
            os.replace(tmp, self.persist_path)

    # ---------- mutation helpers ----------
    async def record_activity(self, kind: str, message: str, target: str = "") -> None:
        async with self._lock:
            self.activity.append({
                "ts": time.time(),
                "kind": kind,
                "target": target,
                "message": message,
            })
            if target:
                self.last_target = target

    async def upsert_table(self, table: TableKnowledge) -> None:
        async with self._lock:
            existing = self.tables.get(table.full_name)
            if existing is None:
                self.tables[table.full_name] = table
            else:
                # merge — keep prior tips, add new ones, refresh metadata
                existing.columns = table.columns or existing.columns
                existing.row_estimate = table.row_estimate or existing.row_estimate
                existing.sample_patterns.update(table.sample_patterns)
                if table.inferred_purpose:
                    existing.inferred_purpose = table.inferred_purpose
                for tip in table.training_tips:
                    if tip not in existing.training_tips:
                        existing.training_tips.append(tip)
                for j in table.suggested_joins:
                    if j not in existing.suggested_joins:
                        existing.suggested_joins.append(j)
                existing.last_seen = table.last_seen
                existing.visits += 1
            self.last_target = table.full_name

    async def add_guidance(self, tip: str) -> None:
        async with self._lock:
            if tip and tip not in self.guidance:
                self.guidance.append(tip)

    async def increment_pass(self) -> None:
        async with self._lock:
            self.passes_completed += 1

    # ---------- Scientist-side mutations ----------
    async def set_scientist_doc(self, doc: str) -> None:
        async with self._lock:
            self.scientist_doc = doc
            self.scientist_passes += 1

    async def add_hypothesis(self, h: str) -> None:
        async with self._lock:
            if h and h not in self.hypotheses:
                self.hypotheses.append(h)
                # bound the list so it stays "lean"
                if len(self.hypotheses) > 50:
                    self.hypotheses = self.hypotheses[-50:]

    async def add_open_question(self, q: str) -> None:
        async with self._lock:
            if q and q not in self.open_questions:
                self.open_questions.append(q)
                if len(self.open_questions) > 50:
                    self.open_questions = self.open_questions[-50:]

    # ---------- Analyst-side mutations ----------
    async def set_analyst_brief(self, brief: str) -> None:
        async with self._lock:
            self.analyst_brief = brief
            self.analyst_passes += 1

    async def set_consumer_trends(self, trends: list[dict[str, Any]]) -> None:
        async with self._lock:
            # cap at 50 to stay lean
            self.consumer_trends = list(trends)[:50]

    async def add_business_insight(self, insight: str) -> None:
        async with self._lock:
            if insight and insight not in self.business_insights:
                self.business_insights.append(insight)
                if len(self.business_insights) > 50:
                    self.business_insights = self.business_insights[-50:]

    # ---------- read helpers ----------
    def snapshot(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "uptime_seconds": time.time() - self.started_at,
            "tables_known": len(self.tables),
            "passes_completed": self.passes_completed,
            "last_target": self.last_target,
            "guidance_count": len(self.guidance),
            "recent_activity": list(self.activity)[-25:],
            "scientist_passes": self.scientist_passes,
            "scientist_doc_chars": len(self.scientist_doc),
            "hypotheses_count": len(self.hypotheses),
            "open_questions_count": len(self.open_questions),
            "analyst_passes": self.analyst_passes,
            "analyst_brief_chars": len(self.analyst_brief),
            "business_insights_count": len(self.business_insights),
            "consumer_trends_count": len(self.consumer_trends),
        }

    def context_for_chat(self, max_tables: int = 40) -> str:
        """Compact textual snapshot of what we know, fed to Claude as context."""
        lines: list[str] = []
        lines.append(f"Catalog passes completed: {self.passes_completed}")
        lines.append(f"Tables known: {len(self.tables)}")
        if self.guidance:
            lines.append("Operator guidance learned so far:")
            for g in self.guidance[-20:]:
                lines.append(f"  - {g}")
        lines.append("Tables:")
        for tbl in list(self.tables.values())[:max_tables]:
            cols = ", ".join(
                f"{c.get('name')}:{c.get('type','?')}" for c in (tbl.columns or [])[:12]
            )
            lines.append(
                f"  • {tbl.full_name} — {tbl.inferred_purpose or 'purpose: tbd'}"
                f" | cols=[{cols}] | rows~{tbl.row_estimate}"
            )
            for tip in tbl.training_tips[:3]:
                lines.append(f"      tip: {tip}")
        return "\n".join(lines)

    def context_for_scientist_chat(self, max_tables: int = 40) -> str:
        """Compact context for the Scientist persona — librarian's notes + lean lab notebook."""
        librarian = self.context_for_chat(max_tables=max_tables)
        sci_lines: list[str] = ["", "Scientist lean knowledge document (auto-curated):"]
        if self.scientist_doc:
            # keep it lean — last ~6KB is plenty for a prompt
            doc = self.scientist_doc[-6000:]
            sci_lines.append(doc)
        else:
            sci_lines.append("(empty — first scientist pass not yet complete)")
        if self.hypotheses:
            sci_lines.append("")
            sci_lines.append("Live hypotheses:")
            for h in self.hypotheses[-15:]:
                sci_lines.append(f"  - {h}")
        if self.open_questions:
            sci_lines.append("")
            sci_lines.append("Open questions to investigate:")
            for q in self.open_questions[-15:]:
                sci_lines.append(f"  - {q}")
        return librarian + "\n" + "\n".join(sci_lines)

    def context_for_analyst_chat(self, max_tables: int = 40) -> str:
        """Compact context for the Analyst persona — librarian + scientist + trends + brief."""
        sci_context = self.context_for_scientist_chat(max_tables=max_tables)
        ana_lines: list[str] = ["", "Analyst lean business briefing (auto-curated):"]
        if self.analyst_brief:
            # keep it lean — last ~6KB
            ana_lines.append(self.analyst_brief[-6000:])
        else:
            ana_lines.append("(empty — first analyst pass not yet complete)")
        if self.consumer_trends:
            ana_lines.append("")
            ana_lines.append("Tracked consumer trends:")
            for t in self.consumer_trends[:15]:
                ana_lines.append(
                    f"  - [{t.get('category','trend')}] {t.get('title','')}"
                )
        if self.business_insights:
            ana_lines.append("")
            ana_lines.append("Live business insights:")
            for ins in self.business_insights[-15:]:
                ana_lines.append(f"  - {ins}")
        return sci_context + "\n" + "\n".join(ana_lines)
