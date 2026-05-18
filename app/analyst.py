"""The Insights Analyst — a third-stage business strategy agent.

Where the Librarian *catalogs* and the Scientist *interrogates* the data, the
Analyst *contextualises* it against the outside world. It runs as its own
asyncio background task and fuses three inputs every pass:

  1. The Librarian's accumulated `tables` (what we have).
  2. The Scientist's lean lab notebook + live hypotheses (how we'd model it).
  3. An external consumer-trends feed (what the market is doing).

It then writes a *lean* evolving Analyst Briefing — bounded per section so it
never bloats — that translates the data warehouse + modeling thinking into
business-relevant insights, opportunities and risks framed in language a
product/strategy leader would actually use.

The Analyst never overwrites Librarian or Scientist state; it only *reads*
their fields and *writes* its own (`analyst_brief`, `business_insights`,
`consumer_trends`).

The consumer-trends feed is pluggable:
  * If ``CONSUMER_TRENDS_URL`` is set, the Analyst fetches a JSON list of
    ``{"title": str, "category": str, "keywords": [str]}`` objects from it.
  * Otherwise it falls back to a curated built-in feed so the app stays
    end-to-end interactive offline.
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any

import httpx

from .config import settings
from .knowledge import KnowledgeStore, TableKnowledge

log = logging.getLogger("data_librarian.analyst")


# ---------- built-in consumer-trends feed (offline-safe fallback) ----------
# Each trend: a short title, a coarse category, and the keywords used to
# correlate it against catalog tables/columns. Keep this list tight; the goal
# is a *lean* briefing, not an exhaustive market report.
DEFAULT_CONSUMER_TRENDS: list[dict[str, Any]] = [
    {
        "title": "Sustained price sensitivity from post-inflation consumers",
        "category": "macro",
        "keywords": ["price", "amount", "discount", "promo", "coupon", "cost", "revenue"],
    },
    {
        "title": "Subscription fatigue — consumers actively pruning recurring spend",
        "category": "monetisation",
        "keywords": ["subscription", "plan", "renewal", "billing", "tier", "membership"],
    },
    {
        "title": "Loyalty program redesign — points are out, perks are in",
        "category": "loyalty",
        "keywords": ["loyalty", "reward", "points", "redeem", "tier", "benefit"],
    },
    {
        "title": "Mobile-first / app-first commerce overtaking desktop",
        "category": "channel",
        "keywords": ["device", "channel", "platform", "source", "app", "mobile", "web"],
    },
    {
        "title": "Personalisation expectations: relevant > frequent",
        "category": "engagement",
        "keywords": ["customer", "user", "segment", "preference", "profile", "recommendation"],
    },
    {
        "title": "BNPL and flexible payment normalisation",
        "category": "payments",
        "keywords": ["payment", "method", "installment", "bnpl", "credit", "card"],
    },
    {
        "title": "Hyper-local fulfilment & same-day expectations",
        "category": "logistics",
        "keywords": ["region", "country", "city", "zip", "address", "warehouse", "ship", "fulfillment"],
    },
    {
        "title": "Sustainability claims influencing purchase consideration",
        "category": "brand",
        "keywords": ["category", "product", "origin", "material", "sku"],
    },
    {
        "title": "Churn-by-friction: small UX issues drive cancellations",
        "category": "retention",
        "keywords": ["status", "churn", "cancel", "active", "inactive", "session"],
    },
    {
        "title": "Live-event & seasonal demand spikes outsize the baseline",
        "category": "seasonality",
        "keywords": ["date", "time", "season", "holiday", "_at", "_ts", "timestamp"],
    },
]


def _short(full_name: str) -> str:
    return full_name.split(".")[-1]


# ---------- correlation engine ----------
def _table_keyword_corpus(tk: TableKnowledge) -> set[str]:
    """All lower-case tokens we'll search a trend's keywords against."""
    tokens: set[str] = set()
    tokens.update(_short(tk.full_name).lower().split("_"))
    for c in tk.columns or []:
        name = (c.get("name") or "").lower()
        if not name:
            continue
        tokens.add(name)
        tokens.update(name.split("_"))
    purpose = (tk.inferred_purpose or "").lower()
    if purpose:
        tokens.update(t for t in purpose.replace("/", " ").replace(",", " ").split() if t)
    return tokens


def _trend_matches(trend: dict[str, Any], corpus: set[str]) -> list[str]:
    """Return the keywords from ``trend`` that fired against ``corpus``."""
    matched: list[str] = []
    for kw in trend.get("keywords") or []:
        k = kw.lower()
        # match either full token or substring (e.g. "amount" hits "amount_usd")
        if k in corpus or any(k in tok for tok in corpus):
            matched.append(kw)
    return matched


def _insight_for_match(
    trend: dict[str, Any],
    tk: TableKnowledge,
    matched_keywords: list[str],
    hypotheses: list[str],
) -> str:
    """Synthesise a business-language insight tying a trend to a table."""
    short = _short(tk.full_name)
    # find the actual columns that contributed (for citation)
    matched_cols = [
        c.get("name") for c in (tk.columns or [])
        if any(k.lower() in (c.get("name") or "").lower() for k in matched_keywords)
    ]
    citation = ", ".join(f"`{c}`" for c in matched_cols[:3]) if matched_cols else ""
    cited_in = f" via {citation} in `{tk.full_name}`" if citation else f" in `{tk.full_name}`"

    category = trend.get("category") or "trend"
    title = trend.get("title") or "Consumer trend"

    # try to find a scientist hypothesis touching the same table for extra colour
    related_hyp = next(
        (h for h in hypotheses if short.lower() in h.lower()),
        "",
    )
    hyp_clip = (related_hyp[:160] + "…") if len(related_hyp) > 160 else related_hyp
    hyp_suffix = f" Scientist signal: {hyp_clip}" if hyp_clip else ""

    return (
        f"[{category}] {title} — quantifiable{cited_in}. "
        f"Recommend a focused readout on this table to size the opportunity.{hyp_suffix}"
    )


def _portfolio_insight(
    trend_hit_counts: Counter, tables: list[TableKnowledge]
) -> str | None:
    """A single cross-portfolio observation (kept lean — one line, not a list)."""
    if not trend_hit_counts:
        return None
    top_cat, hits = trend_hit_counts.most_common(1)[0]
    return (
        f"Portfolio view: '{top_cat}' is the dominant external pressure "
        f"({hits} tables exposed across {len(tables)} catalogued) — "
        "treat it as the leading theme for the next planning cycle."
    )


def _build_lean_brief(
    tables: list[TableKnowledge],
    trends: list[dict[str, Any]],
    insights: list[str],
    portfolio_line: str | None,
) -> str:
    """Render the lean Analyst Briefing. Bounded per section."""
    header = [
        "# Analyst Briefing — business insights persona",
        "",
        "_Curated continuously from the Librarian's catalog + the Scientist's lab notebook,_",
        "_correlated against an external consumer-trends feed. Lean by construction:_",
        f"_{len(tables)} tables catalogued · {len(trends)} trends tracked · {len(insights)} live insights._",
        "",
    ]
    body: list[str] = []
    if portfolio_line:
        body += ["## Portfolio view", "", portfolio_line, ""]

    body += ["## Tracked consumer trends", ""]
    for t in trends[:12]:
        cat = t.get("category") or "trend"
        body.append(f"- **[{cat}]** {t.get('title', '')}")
    body.append("")

    body += ["## Business-relevant insights", ""]
    if insights:
        for ins in insights[:20]:
            body.append(f"- {ins}")
    else:
        body.append("- (no correlations yet — waiting for richer catalog notes)")
    body.append("")
    return "\n".join(header + body).strip() + "\n"


# ---------- the agent loop ----------
class AnalystAgent:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()
        self._http: httpx.AsyncClient | None = None

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="data-librarian-analyst")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                self._task.cancel()
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def _fetch_trends(self) -> list[dict[str, Any]]:
        """Fetch the consumer-trends feed; fall back to the built-in list."""
        url = settings.consumer_trends_url.strip()
        if not url:
            return list(DEFAULT_CONSUMER_TRENDS)
        try:
            if self._http is None:
                self._http = httpx.AsyncClient(timeout=10.0)
            resp = await self._http.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                cleaned: list[dict[str, Any]] = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title")
                    if not title:
                        continue
                    cleaned.append({
                        "title": str(title),
                        "category": str(item.get("category") or "trend"),
                        "keywords": [str(k) for k in (item.get("keywords") or []) if k],
                    })
                if cleaned:
                    return cleaned
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to fetch consumer trends from %s: %s", url, exc)
        return list(DEFAULT_CONSUMER_TRENDS)

    async def _run(self) -> None:
        log.info("Analyst starting; will read what the Librarian and Scientist write.")
        await self.store.record_activity(
            "boot", "Analyst online. Reading the room and the market."
        )
        while not self._stopping.is_set():
            try:
                await self._one_pass()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("Analyst pass failed: %s", exc)
                await self.store.record_activity("error", f"Analyst pass failed: {exc}")
            try:
                await asyncio.wait_for(
                    self._stopping.wait(),
                    timeout=settings.analyst_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def _one_pass(self) -> None:
        if not self.store.tables:
            await self.store.record_activity(
                "insight",
                "Nothing catalogued yet — Analyst is waiting on the Librarian.",
            )
            return

        trends = await self._fetch_trends()
        await self.store.set_consumer_trends(trends)
        await self.store.record_activity(
            "insight",
            f"Correlating {len(self.store.tables)} tables against {len(trends)} consumer trends.",
        )

        tables = list(self.store.tables.values())
        hypotheses = list(self.store.hypotheses)

        insights: list[str] = []
        category_hits: Counter = Counter()
        for tk in tables:
            corpus = _table_keyword_corpus(tk)
            for trend in trends:
                matched = _trend_matches(trend, corpus)
                if not matched:
                    continue
                category_hits[trend.get("category") or "trend"] += 1
                insights.append(_insight_for_match(trend, tk, matched, hypotheses))

        # dedupe while preserving order, then bound
        seen: set[str] = set()
        deduped: list[str] = []
        for ins in insights:
            if ins not in seen:
                seen.add(ins)
                deduped.append(ins)
        deduped = deduped[:20]

        for ins in deduped:
            await self.store.add_business_insight(ins)
            await asyncio.sleep(0)

        portfolio_line = _portfolio_insight(category_hits, tables)
        brief = _build_lean_brief(tables, trends, list(self.store.business_insights), portfolio_line)
        await self.store.set_analyst_brief(brief)
        await self.store.persist()
        await self.store.record_activity(
            "insight",
            f"Analyst briefing updated · pass #{self.store.analyst_passes} · "
            f"{len(self.store.business_insights)} insights across "
            f"{len(category_hits)} trend categories.",
        )
