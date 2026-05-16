"""Tiny smoke tests — no external deps required."""
from __future__ import annotations

import asyncio
import os
import tempfile

from app.agent import LiveAgent, _column_patterns, _infer_purpose, _training_tips
from app.knowledge import KnowledgeStore
from app.scientist import (
    ScientistAgent,
    _candidate_targets,
    _candidate_features,
    _modeling_archetype,
    _build_lean_doc,
)
from app.analyst import (
    AnalystAgent,
    DEFAULT_CONSUMER_TRENDS,
    _table_keyword_corpus,
    _trend_matches,
    _build_lean_brief,
)


def test_inference_helpers() -> None:
    cols = [
        {"name": "order_id", "type": "BIGINT"},
        {"name": "customer_id", "type": "BIGINT"},
        {"name": "amount_usd", "type": "DECIMAL(18,2)"},
        {"name": "ordered_at", "type": "TIMESTAMP"},
    ]
    p = _column_patterns(cols)
    assert p["has_primary_key_candidate"]
    assert p["has_timestamp"]
    assert p["has_money"]
    purpose = _infer_purpose("orders", cols).lower()
    assert "fact" in purpose or "transactional" in purpose
    tips = _training_tips("demo.schema.orders", cols, p)
    assert any("ordered_at" in t for t in tips)


def test_agent_pass_against_demo() -> None:
    async def run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(os.path.join(tmp, "k.json"))
            agent = LiveAgent(store)
            await agent._one_pass()
            snap = store.snapshot()
            assert snap["tables_known"] >= 3
            assert snap["passes_completed"] == 1
            ctx = store.context_for_chat()
            assert "customers" in ctx and "orders" in ctx
    asyncio.run(run())


def test_scientist_helpers() -> None:
    from app.knowledge import TableKnowledge
    tk = TableKnowledge(
        full_name="demo.schema.orders",
        columns=[
            {"name": "order_id", "type": "BIGINT"},
            {"name": "customer_id", "type": "BIGINT"},
            {"name": "amount_usd", "type": "DECIMAL(18,2)"},
            {"name": "ordered_at", "type": "TIMESTAMP"},
            {"name": "status", "type": "STRING"},
        ],
        inferred_purpose="Fact / event table",
    )
    targets = _candidate_targets(tk)
    feats = _candidate_features(tk)
    arch = _modeling_archetype(tk)
    assert "amount_usd" in targets or "status" in targets
    assert "ordered_at" in feats or "status" in feats
    assert "time-series" in arch or "transactional" in arch
    doc = _build_lean_doc([tk], ["hyp1"], ["q1"])
    assert "Lab Notebook" in doc
    assert "demo.schema.orders" in doc
    assert "hyp1" in doc and "q1" in doc


def test_scientist_pass_against_demo() -> None:
    async def run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(os.path.join(tmp, "k.json"))
            librarian = LiveAgent(store)
            scientist = ScientistAgent(store)
            await librarian._one_pass()
            await scientist._one_pass()
            assert store.scientist_passes == 1
            assert store.scientist_doc.strip(), "scientist doc should not be empty"
            assert "Lab Notebook" in store.scientist_doc
            # leverages the librarian's tables
            assert "orders" in store.scientist_doc or "customers" in store.scientist_doc
            # at least one hypothesis or open question was emitted
            assert store.hypotheses or store.open_questions
            # context for scientist chat embeds the lab notebook
            ctx = store.context_for_scientist_chat()
            assert "Scientist lean knowledge document" in ctx
            assert "Lab Notebook" in ctx
            # persistence round-trip retains scientist state
            await store.persist()
            store2 = KnowledgeStore(os.path.join(tmp, "k.json"))
            assert store2.scientist_passes == 1
            assert "Lab Notebook" in store2.scientist_doc
    asyncio.run(run())


def test_analyst_helpers() -> None:
    from app.knowledge import TableKnowledge
    tk = TableKnowledge(
        full_name="demo.schema.orders",
        columns=[
            {"name": "order_id", "type": "BIGINT"},
            {"name": "customer_id", "type": "BIGINT"},
            {"name": "amount_usd", "type": "DECIMAL(18,2)"},
            {"name": "ordered_at", "type": "TIMESTAMP"},
            {"name": "status", "type": "STRING"},
            {"name": "payment_method", "type": "STRING"},
        ],
        inferred_purpose="Fact / event table",
    )
    corpus = _table_keyword_corpus(tk)
    # tokens from the table name + column names should be present
    assert "orders" in corpus and "amount_usd" in corpus and "payment_method" in corpus
    # The "price sensitivity" trend keys against 'amount'/'price'/etc → should fire
    price_trend = next(t for t in DEFAULT_CONSUMER_TRENDS if "price" in t["title"].lower())
    assert _trend_matches(price_trend, corpus), "price sensitivity trend should match orders.amount_usd"
    # The "BNPL" trend keys against 'payment'/'method' → should fire
    pay_trend = next(t for t in DEFAULT_CONSUMER_TRENDS if "BNPL" in t["title"])
    assert _trend_matches(pay_trend, corpus)
    # brief renders the key sections
    brief = _build_lean_brief(
        [tk], DEFAULT_CONSUMER_TRENDS,
        ["[macro] Sustained price sensitivity — quantifiable via `amount_usd` in `demo.schema.orders`."],
        "Portfolio view: 'macro' is the dominant external pressure.",
    )
    assert "Analyst Briefing" in brief
    assert "Tracked consumer trends" in brief
    assert "Business-relevant insights" in brief
    assert "demo.schema.orders" in brief


def test_analyst_pass_against_demo() -> None:
    async def run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = KnowledgeStore(os.path.join(tmp, "k.json"))
            librarian = LiveAgent(store)
            scientist = ScientistAgent(store)
            analyst = AnalystAgent(store)
            await librarian._one_pass()
            await scientist._one_pass()
            await analyst._one_pass()
            # analyst writes its own state
            assert store.analyst_passes == 1
            assert store.analyst_brief.strip(), "analyst brief should not be empty"
            assert "Analyst Briefing" in store.analyst_brief
            # leverages the librarian's tables in the brief
            assert "orders" in store.analyst_brief or "customers" in store.analyst_brief
            # consumer trends were loaded
            assert len(store.consumer_trends) >= 1
            # at least one business insight was derived from the demo schema
            assert store.business_insights, "expected at least one business insight"
            # analyst context for chat includes the brief + tracked trends
            ctx = store.context_for_analyst_chat()
            assert "Analyst lean business briefing" in ctx
            assert "Tracked consumer trends" in ctx
            # analyst does not stomp scientist or librarian state
            assert store.scientist_passes == 1
            assert store.tables, "librarian tables must still be present"
            # persistence round-trip retains analyst state
            await store.persist()
            store2 = KnowledgeStore(os.path.join(tmp, "k.json"))
            assert store2.analyst_passes == 1
            assert "Analyst Briefing" in store2.analyst_brief
            assert store2.consumer_trends and store2.business_insights
    asyncio.run(run())


if __name__ == "__main__":
    test_inference_helpers()
    test_agent_pass_against_demo()
    test_scientist_helpers()
    test_scientist_pass_against_demo()
    test_analyst_helpers()
    test_analyst_pass_against_demo()
    print("ok")
