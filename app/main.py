"""FastAPI entry point — chat, status, SSE heartbeat, static UI."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .agent import LiveAgent
from .claude_client import claude_client
from .config import settings
from .knowledge import KnowledgeStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

store = KnowledgeStore(settings.knowledge_path)
agent = LiveAgent(store)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    agent.start()
    try:
        yield
    finally:
        await agent.stop()
        await claude_client.aclose()


app = FastAPI(title="Data Librarian", version="0.1.0", lifespan=lifespan)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# ---------- API ----------
class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


class ChatResponse(BaseModel):
    reply: str
    knowledge_passes: int
    tables_known: int


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


@app.get("/api/status")
async def api_status() -> JSONResponse:
    snap = store.snapshot()
    snap["databricks_configured"] = settings.databricks_configured
    snap["claude_configured"] = settings.claude_configured
    snap["learn_interval_seconds"] = settings.learn_interval_seconds
    return JSONResponse(snap)


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest) -> ChatResponse:
    context = store.context_for_chat()
    reply = await claude_client.chat(req.message, context, req.history)
    return ChatResponse(
        reply=reply,
        knowledge_passes=store.passes_completed,
        tables_known=len(store.tables),
    )


@app.get("/api/stream")
async def api_stream() -> EventSourceResponse:
    """Server-sent events stream that drives the 'alive' UI.

    Emits a heartbeat + the latest activity entry every second.
    """
    async def gen() -> AsyncIterator[dict]:
        last_index = 0
        while True:
            snap = store.snapshot()
            recent = snap["recent_activity"]
            new_items = recent[last_index:] if last_index < len(recent) else []
            last_index = len(recent)
            payload = {
                "uptime": snap["uptime_seconds"],
                "tables_known": snap["tables_known"],
                "passes": snap["passes_completed"],
                "last_target": snap["last_target"],
                "new_activity": new_items,
            }
            yield {"event": "tick", "data": json.dumps(payload)}
            await asyncio.sleep(1.0)

    return EventSourceResponse(gen())
