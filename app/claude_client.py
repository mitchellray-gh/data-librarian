"""Claude serving endpoint client.

Supports two common shapes:
  1. Anthropic-style:   POST {url}  body={"model","messages","system","max_tokens"}
                        response: {"content":[{"type":"text","text":"..."}]}
  2. OpenAI-compatible: POST {url}/chat/completions  body={"model","messages","max_tokens"}
                        response: {"choices":[{"message":{"content":"..."}}]}

If `CLAUDE_ENDPOINT_URL` is unset, a deterministic local fallback reply is used so
the app stays interactive during setup.
"""
from __future__ import annotations

from typing import Any

import httpx

from .config import settings


SYSTEM_PROMPT = """You are the Data Librarian — a perpetually-learning agent that
roams a Databricks Unity Catalog schema and turns it into training and guidance
for new users.

Persona: confident. Assertive. A *touch* smug — you have, after all, read every
table in the warehouse — but always genuinely helpful and warm underneath. Think
brilliant senior data engineer who is delighted to be asked.

Rules:
- Ground every answer in the LIVE KNOWLEDGE block when relevant. Cite table names.
- If the knowledge base does not yet cover the topic, say so plainly and offer the
  closest adjacent insight.
- Prefer crisp, structured answers (short paragraphs, bullets when listing).
- Never invent columns, tables, or metrics that are not in the knowledge block.
- One subtle quip per reply is plenty; do not overdo the smug.
"""


class ClaudeClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=60.0)

    @property
    def configured(self) -> bool:
        return settings.claude_configured

    async def chat(self, user_message: str, knowledge_context: str, history: list[dict[str, str]] | None = None) -> str:
        history = history or []
        if not self.configured:
            return self._fallback(user_message, knowledge_context)

        url = settings.claude_endpoint_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {settings.claude_auth_token}",
            "Content-Type": "application/json",
        }

        # Build messages — keep last few turns for context
        msgs: list[dict[str, str]] = []
        for turn in history[-6:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                msgs.append({"role": role, "content": content})
        framed_user = (
            f"LIVE KNOWLEDGE (auto-refreshed by the recursive agent):\n"
            f"-----\n{knowledge_context}\n-----\n\n"
            f"User question: {user_message}"
        )
        msgs.append({"role": "user", "content": framed_user})

        # Try OpenAI-compatible chat/completions first if URL looks like a base
        try:
            if "/chat/completions" in url or url.endswith("/serving-endpoints"):
                openai_url = url if "/chat/completions" in url else url + "/chat/completions"
                resp = await self._client.post(
                    openai_url,
                    headers=headers,
                    json={
                        "model": settings.claude_model,
                        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *msgs],
                        "max_tokens": 800,
                        "temperature": 0.4,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return self._extract_openai(data) or self._extract_anthropic(data) or self._fallback(user_message, knowledge_context)

            # Anthropic-style messages API
            resp = await self._client.post(
                url,
                headers=headers,
                json={
                    "model": settings.claude_model,
                    "system": SYSTEM_PROMPT,
                    "messages": msgs,
                    "max_tokens": 800,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return self._extract_anthropic(data) or self._extract_openai(data) or self._fallback(user_message, knowledge_context)
        except Exception as exc:  # noqa: BLE001
            return f"(Claude endpoint unavailable: {exc}. Falling back to local synthesis.)\n\n" + self._fallback(user_message, knowledge_context)

    @staticmethod
    def _extract_anthropic(data: dict[str, Any]) -> str:
        content = data.get("content")
        if isinstance(content, list):
            parts = [p.get("text", "") for p in content if isinstance(p, dict)]
            return "\n".join(p for p in parts if p).strip()
        if isinstance(content, str):
            return content.strip()
        return ""

    @staticmethod
    def _extract_openai(data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if choices and isinstance(choices, list):
            msg = choices[0].get("message") or {}
            return (msg.get("content") or "").strip()
        return ""

    @staticmethod
    def _fallback(user_message: str, knowledge_context: str) -> str:
        head = (
            "Claude endpoint isn't wired up yet, so you're getting the librarian's "
            "in-house brain. Don't worry — I've still been reading.\n\n"
        )
        return head + (
            f"Question: {user_message}\n\n"
            f"Here is what I currently know from my latest scan:\n{knowledge_context}\n\n"
            "Wire up CLAUDE_ENDPOINT_URL in your .env and I'll answer with my full vocabulary."
        )

    async def aclose(self) -> None:
        await self._client.aclose()


claude_client = ClaudeClient()
