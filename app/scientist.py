"""The Scientist — a curious, investigative second-stage agent.

Where the Librarian *catalogs* the schema, the Scientist *interrogates* it. It
runs as its own asyncio background task on a slower cadence and consumes
whatever the Librarian has accumulated so far. Each Scientist pass:

  1. Reads the latest `KnowledgeStore.tables` (the Librarian's notes).
  2. Looks deeper at the *underlying* shape of the data — cardinality,
     value distributions, candidate targets, candidate features, modeling
     archetypes, data-quality smells, time-series & cohort opportunities.
  3. Forms hypotheses ("`orders.amount_usd` looks log-normal, predict with
     log-target regression") and open questions ("is `country` the right
     cohort dimension or is it `region`?").
  4. Re-writes a *lean* evolving knowledge document — capped per-section so
     it never bloats — and persists it.

The Scientist never overwrites Librarian state; it only *reads* `tables` and
*writes* its own fields (`scientist_doc`, `hypotheses`, `open_questions`).
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any

from .config import settings
from .knowledge import KnowledgeStore, TableKnowledge

log = logging.getLogger("data_librarian.scientist")


# ---------- modeling/science heuristics ----------
_TARGET_HINTS = (
    "amount", "price", "revenue", "cost", "score", "rating", "quantity",
    "qty", "total", "value", "duration", "latency", "churn", "label",
    "target", "outcome", "is_", "has_", "status",
)
_FEATURE_SKIP = ("_id", "uuid", "guid")
_TIME_HINTS = ("_at", "_ts", "timestamp", "date", "time")


def _short(full_name: str) -> str:
    return full_name.split(".")[-1]


def _cardinality_band(distinct: int, sample_size: int) -> str:
    """Map a sample's distinct-value count to a coarse cardinality bucket."""
    if sample_size <= 0:
        return "unknown"
    ratio = distinct / max(sample_size, 1)
    if distinct == 1:
        return "constant"
    if distinct == sample_size and sample_size >= 5:
        return "near-unique"
    if ratio >= 0.8:
        return "high"
    if ratio >= 0.3:
        return "medium"
    return "low"


def _candidate_targets(tk: TableKnowledge) -> list[str]:
    out: list[str] = []
    for c in tk.columns or []:
        cname = (c.get("name") or "")
        cl = cname.lower()
        if any(h in cl for h in _TARGET_HINTS) and not cl.endswith("_id"):
            out.append(cname)
    return out[:5]


def _candidate_features(tk: TableKnowledge) -> list[str]:
    out: list[str] = []
    for c in tk.columns or []:
        cname = (c.get("name") or "")
        cl = cname.lower()
        if not cname or cl == "id":
            continue
        if any(cl.endswith(s) for s in _FEATURE_SKIP):
            # IDs are usually not features by themselves, but they can become
            # cohort keys — flag them as such elsewhere.
            continue
        out.append(cname)
    return out[:8]


def _quality_smells(tk: TableKnowledge) -> list[str]:
    """Detect smells from the Librarian's sample patterns."""
    smells: list[str] = []
    for col, info in (tk.sample_patterns or {}).items():
        top = info.get("top_values") or []
        distinct = info.get("distinct_in_sample") or 0
        sample_size = sum(cnt for _, cnt in top) if top else 0
        if sample_size and top:
            top_val, top_cnt = top[0]
            dom = top_cnt / sample_size
            if dom >= 0.9 and distinct > 1:
                smells.append(
                    f"`{col}` is dominated by `{top_val}` (~{int(dom * 100)}% in sample) — "
                    "watch for class imbalance / low signal."
                )
            if str(top_val).lower() in ("none", "null", ""):
                smells.append(f"`{col}` has nulls in the top sampled values — confirm imputation strategy.")
        if distinct == 1:
            smells.append(f"`{col}` looks constant in sample — likely useless as a feature.")
    return smells[:5]


def _modeling_archetype(tk: TableKnowledge) -> str:
    """Classify the table from a modeling-not-cataloging point of view."""
    purpose = (tk.inferred_purpose or "").lower()
    cnames = {(c.get("name") or "").lower() for c in tk.columns or []}
    has_ts = any(any(h in c for h in _TIME_HINTS) for c in cnames)
    has_money = any(h in c for c in cnames for h in ("amount", "price", "revenue", "cost"))
    if "fact" in purpose or "event" in purpose:
        if has_ts and has_money:
            return "time-series regression / forecasting candidate (event-level monetary signal)"
        if has_ts:
            return "event stream — sessionization, funnel, survival analysis candidate"
        return "transactional fact — aggregate-then-model"
    if "dimension" in purpose:
        return "feature-engineering source — join into facts to enrich models"
    if "snapshot" in purpose:
        return "panel / longitudinal data — diff-in-diff or change-point analysis"
    return "general — start with EDA before committing to a model family"


def _per_table_section(tk: TableKnowledge) -> str:
    short = _short(tk.full_name)
    targets = _candidate_targets(tk)
    feats = _candidate_features(tk)
    smells = _quality_smells(tk)
    archetype = _modeling_archetype(tk)

    # cardinality summary from sample patterns (lean — top 4 cols only)
    card_lines: list[str] = []
    for col, info in list((tk.sample_patterns or {}).items())[:4]:
        top = info.get("top_values") or []
        sample_size = sum(cnt for _, cnt in top) if top else 0
        band = _cardinality_band(info.get("distinct_in_sample") or 0, sample_size)
        if top:
            top_val, _ = top[0]
            card_lines.append(f"  - `{col}`: cardinality={band}, mode=`{top_val}`")
        else:
            card_lines.append(f"  - `{col}`: cardinality={band}")

    parts = [f"### {tk.full_name}", f"- archetype: {archetype}"]
    if targets:
        parts.append(f"- candidate targets: {', '.join(f'`{t}`' for t in targets)}")
    if feats:
        parts.append(f"- candidate features: {', '.join(f'`{f}`' for f in feats)}")
    if tk.suggested_joins:
        parts.append(f"- enrich via: {tk.suggested_joins[0]}"
                     + (f"  (+{len(tk.suggested_joins)-1} more)" if len(tk.suggested_joins) > 1 else ""))
    if card_lines:
        parts.append("- cardinality (from sample):")
        parts.extend(card_lines)
    if smells:
        parts.append("- data-quality smells:")
        parts.extend(f"  - {s}" for s in smells)
    return "\n".join(parts)


def _generate_hypotheses(tables: list[TableKnowledge]) -> list[str]:
    hyps: list[str] = []
    archetype_counter: Counter = Counter()
    for tk in tables:
        archetype = _modeling_archetype(tk)
        archetype_counter[archetype.split(" ")[0]] += 1
        targets = _candidate_targets(tk)
        if targets and any("amount" in t.lower() or "price" in t.lower() for t in targets):
            hyps.append(
                f"`{_short(tk.full_name)}.{targets[0]}` is a strong regression target; "
                "try a log-transform — monetary distributions are usually heavy-tailed."
            )
        if "time-series" in archetype:
            hyps.append(
                f"`{_short(tk.full_name)}` supports time-series modeling — "
                "begin with a daily/weekly aggregate and a seasonal-naive baseline."
            )
        if "dimension" in (tk.inferred_purpose or "").lower():
            hyps.append(
                f"`{_short(tk.full_name)}` is a dimension — denormalize the top 3 attributes "
                "into facts to lift baseline model performance."
            )
    # global hypothesis
    if archetype_counter.get("time-series", 0) >= 1 and archetype_counter.get("feature-engineering", 0) >= 1:
        hyps.append(
            "Schema supports a classic supervised pipeline: dimension features ⨝ fact events → "
            "time-aware train/validation split."
        )
    # dedupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for h in hyps:
        if h not in seen:
            seen.add(h)
            deduped.append(h)
    return deduped[:12]


def _generate_open_questions(tables: list[TableKnowledge]) -> list[str]:
    qs: list[str] = []
    for tk in tables:
        cnames = {(c.get("name") or "").lower() for c in tk.columns or []}
        if any("country" in c or "region" in c or "city" in c for c in cnames):
            qs.append(f"What is the right geographic granularity for cohorting `{_short(tk.full_name)}`?")
        if "fact" in (tk.inferred_purpose or "").lower():
            qs.append(f"What is the natural grain of `{_short(tk.full_name)}` — one row per what?")
        if not tk.sample_patterns:
            qs.append(f"`{_short(tk.full_name)}` has no value samples yet — is a SQL warehouse needed?")
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:10]


def _build_lean_doc(tables: list[TableKnowledge], hypotheses: list[str], questions: list[str]) -> str:
    """Render the entire lean knowledge document. Bounded by table-section count."""
    header = [
        "# Lab Notebook — Scientist persona",
        "",
        "_Curated continuously from the Librarian's catalog notes. Lean by construction:_",
        f"_{len(tables)} tables analyzed · {len(hypotheses)} hypotheses · {len(questions)} open questions._",
        "",
        "## Modeling map",
        "",
    ]
    body: list[str] = []
    # Cap to the most-visited tables to keep the doc lean
    ranked = sorted(tables, key=lambda t: (-(t.visits or 0), t.full_name))[:30]
    for tk in ranked:
        body.append(_per_table_section(tk))
        body.append("")
    if hypotheses:
        body.append("## Working hypotheses")
        body.append("")
        for h in hypotheses:
            body.append(f"- {h}")
        body.append("")
    if questions:
        body.append("## Open questions")
        body.append("")
        for q in questions:
            body.append(f"- {q}")
        body.append("")
    return "\n".join(header + body).strip() + "\n"


# ---------- the agent loop ----------
class ScientistAgent:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="data-librarian-scientist")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()

    async def _run(self) -> None:
        log.info("Scientist starting; will read what the Librarian writes.")
        await self.store.record_activity("boot", "Scientist online. Sharpening pencils.")
        while not self._stopping.is_set():
            try:
                await self._one_pass()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("Scientist pass failed: %s", exc)
                await self.store.record_activity("error", f"Scientist pass failed: {exc}")
            try:
                await asyncio.wait_for(
                    self._stopping.wait(),
                    timeout=settings.scientist_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def _one_pass(self) -> None:
        # Wait politely for the Librarian to actually have something to look at.
        if not self.store.tables:
            await self.store.record_activity(
                "science", "Nothing in the catalog yet — waiting for the Librarian."
            )
            return

        await self.store.record_activity(
            "science", f"Investigating {len(self.store.tables)} tables for modeling angles."
        )
        # Snapshot the tables — readers don't take the lock, but copy the list so a
        # concurrent Librarian upsert doesn't mutate underneath us.
        tables = list(self.store.tables.values())
        hypotheses = _generate_hypotheses(tables)
        questions = _generate_open_questions(tables)

        # Persist hypotheses/questions into the store (deduped, bounded).
        for h in hypotheses:
            await self.store.add_hypothesis(h)
            await asyncio.sleep(0)
        for q in questions:
            await self.store.add_open_question(q)
            await asyncio.sleep(0)

        doc = _build_lean_doc(tables, self.store.hypotheses, self.store.open_questions)
        await self.store.set_scientist_doc(doc)
        await self.store.persist()
        await self.store.record_activity(
            "hypothesis",
            f"Lab notebook updated · pass #{self.store.scientist_passes} · "
            f"{len(self.store.hypotheses)} hypotheses, {len(self.store.open_questions)} open questions.",
        )
