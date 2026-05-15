"""Tiny smoke tests — no external deps required."""
from __future__ import annotations

import asyncio
import os
import tempfile

from app.agent import LiveAgent, _column_patterns, _infer_purpose, _training_tips
from app.knowledge import KnowledgeStore


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


if __name__ == "__main__":
    test_inference_helpers()
    test_agent_pass_against_demo()
    print("ok")
