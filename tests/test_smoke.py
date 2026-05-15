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


if __name__ == "__main__":
    test_inference_helpers()
    test_agent_pass_against_demo()
    test_scientist_helpers()
    test_scientist_pass_against_demo()
    print("ok")
