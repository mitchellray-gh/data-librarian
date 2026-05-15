# 📚 Data Librarian

A perpetually-awake AI agent that recursively crawls a Databricks Unity Catalog
schema, builds up training, guidance, inferences, modeling notes and pattern
analysis as it goes, and answers questions through a sleek white chat UI backed
by a Claude serving endpoint.

> Persona: confident, assertive, a *touch* smug — but genuinely warm and helpful.
> It has, after all, read every table in your warehouse.

## What it does

- **Live, recursive learning loop** — a background asyncio task walks
  `catalog → schema → tables → columns → samples` on a configurable interval,
  forever. Each pass *enriches* the knowledge base; nothing is ever forgotten.
- **Inference & pattern analysis** — infers fact vs. dimension tables, detects
  primary-key candidates, timestamps and monetary columns, and proposes
  foreign-key joins across the schema.
- **Training & guidance synthesis** — turns observations into per-table tips
  ("filter `orders` on `ordered_at` for partition pruning") and global guidance
  ("schema looks star-shaped, ~5 fact / ~12 dimension tables").
- **Sleek "alive" chat UI** — heartbeat ring, live "currently studying"
  indicator, scrolling activity ticker, and a chat panel grounded in the
  librarian's growing knowledge.
- **Pluggable endpoints** — Databricks workspace and Claude serving endpoint are
  set later via `.env`. Until they're configured the app runs end-to-end against
  a built-in demo schema and a local fallback responder.

## Layout

```
app/
  main.py              FastAPI app: /, /api/status, /api/chat, /api/stream (SSE)
  agent.py             Recursive live learning agent (background asyncio task)
  knowledge.py         Persistent knowledge store (tables, patterns, guidance, activity)
  databricks_client.py Databricks SDK wrapper (graceful demo fallback)
  claude_client.py     Claude serving endpoint client (Anthropic + OpenAI shapes)
  config.py            .env-driven settings
  static/              index.html, styles.css, app.js  ← the white chat UI
tests/
  test_smoke.py        Inference + agent-pass smoke tests
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env             # leave blank to run against the built-in demo schema
PYTHONPATH=. uvicorn app.main:app --reload
```

Open http://localhost:8000 — the librarian is already awake and reading.

## Configuration

Edit `.env` (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN` | Workspace URL + PAT |
| `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA` | Unity Catalog target the agent will recurse over |
| `CLAUDE_ENDPOINT_URL` | Your Claude serving endpoint (Databricks model serving, Anthropic, or OpenAI-compatible) |
| `CLAUDE_API_KEY` | Bearer token for the Claude endpoint (falls back to `DATABRICKS_TOKEN`) |
| `CLAUDE_MODEL` | Model identifier sent in the request body |
| `LEARN_INTERVAL_SECONDS` | How often the recursive pass runs (default `15`) |
| `SAMPLE_ROW_LIMIT` | Max rows the agent will sample per table (default `20`) |
| `KNOWLEDGE_PATH` | Where the persistent knowledge JSON lives |

## API

- `GET  /`           — the chat UI
- `GET  /api/status` — live snapshot (uptime, passes, tables, recent activity, config)
- `POST /api/chat`   — `{message, history}` → `{reply, knowledge_passes, tables_known}`
- `GET  /api/stream` — Server-Sent Events; one `tick` per second driving the UI's "alive" feel

## Tests

```bash
PYTHONPATH=. python tests/test_smoke.py
```

Validates the inference helpers and runs one full agent pass against the demo
schema (no network required).
