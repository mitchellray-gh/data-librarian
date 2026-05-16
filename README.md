# 📚 Data Librarian + 🔬 Scientist

A perpetually-awake **two-agent** AI system for a Databricks Unity Catalog
schema. The Librarian recursively crawls the catalog and accumulates training,
guidance, inference and pattern notes. The Scientist reads what the Librarian
writes and continuously curates a **lean, evolving lab notebook** focused on
modeling, distributions, candidate targets/features, hypotheses and open
questions. Both answer through a sleek white chat UI backed by a Claude
serving endpoint — switch between them with a persona toggle.

> **Librarian** — confident, assertive, a *touch* smug — but warm. "I have read every table."
> **Scientist** — curious, investigative, hypothesis-driven. "What's the data-generating process here?"

## What it does

- **Live, recursive learning loop (Librarian)** — a background asyncio task
  walks `catalog → schema → tables → columns → samples` on a configurable
  interval, forever. Each pass *enriches* the knowledge base; nothing is ever
  forgotten.
- **Inference & pattern analysis (Librarian)** — infers fact vs. dimension
  tables, detects primary-key candidates, timestamps and monetary columns, and
  proposes foreign-key joins across the schema.
- **Deeper modeling investigation (Scientist)** — runs as its own background
  task on a slower **hourly** cadence. Reads the Librarian's accumulated
  `tables`, derives modeling archetypes (forecasting, EDA, panel,
  feature-engineering source), classifies columns into candidate targets vs.
  features, bands cardinality, sniffs out data-quality smells, and forms
  hypotheses + open questions.
- **Lean knowledge document** — the Scientist continuously rewrites a markdown
  *Lab Notebook* (capped per-section so it stays lean) that lives in the
  knowledge store, persists across restarts, and is exposed at
  `GET /api/scientist/doc` and rendered live in the UI.
- **Persona-aware chat** — `POST /api/chat` accepts `persona: "librarian" |
  "scientist"`. The Scientist persona is fed the Librarian's catalog *plus*
  the lean lab notebook + live hypotheses + open questions.
- **Sleek "alive" chat UI** — heartbeat ring, live "currently studying"
  indicator, scrolling activity ticker (science entries styled distinctly),
  expandable Lab Notebook panel, and a persona dropdown in the composer.
- **Pluggable endpoints** — Databricks workspace and Claude serving endpoint
  are set later via `.env`. Until configured, the app runs end-to-end against
  a built-in demo schema and a local fallback responder.

## Layout

```
app/
  main.py              FastAPI app: /, /api/status, /api/chat, /api/stream (SSE), /api/scientist/doc
  agent.py             Librarian — recursive live learning agent (background asyncio task)
  scientist.py         Scientist — investigative second-stage agent that writes the lean lab notebook
  knowledge.py         Persistent knowledge store (tables, patterns, guidance, activity, scientist doc)
  databricks_client.py Databricks SDK wrapper (graceful demo fallback)
  claude_client.py     Claude serving endpoint client + Librarian/Scientist system prompts
  config.py            .env-driven settings
  static/              index.html, styles.css, app.js  ← the white chat UI
tests/
  test_smoke.py        Inference + Librarian-pass + Scientist-pass smoke tests
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env             # leave blank to run against the built-in demo schema
PYTHONPATH=. uvicorn app.main:app --reload
```

Open http://localhost:8000 — both agents are already awake. Use the persona
dropdown to ask the Librarian *or* the Scientist.

## Configuration

Edit `.env` (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN` | Workspace URL + PAT |
| `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA` | Unity Catalog target the Librarian recurses over |
| `CLAUDE_ENDPOINT_URL` | Your Claude serving endpoint (Databricks model serving, Anthropic, or OpenAI-compatible) |
| `CLAUDE_API_KEY` | Bearer token for the Claude endpoint (falls back to `DATABRICKS_TOKEN`) |
| `CLAUDE_MODEL` | Model identifier sent in the request body |
| `LEARN_INTERVAL_SECONDS` | How often the Librarian's recursive pass runs (default `15`) |
| `SCIENTIST_INTERVAL_SECONDS` | How often the Scientist re-curates the lab notebook (default `3600` — once per hour) |
| `SAMPLE_ROW_LIMIT` | Max rows the agent will sample per table (default `20`) |
| `KNOWLEDGE_PATH` | Where the persistent knowledge JSON lives |

## API

- `GET  /`                    — the chat UI
- `GET  /api/status`          — live snapshot (uptime, passes, scientist passes, hypotheses/question counts, recent activity, config)
- `POST /api/chat`            — `{message, history, persona}` → `{reply, knowledge_passes, tables_known, persona}`
- `GET  /api/stream`          — Server-Sent Events; one `tick` per second driving the UI's "alive" feel
- `GET  /api/scientist/doc`   — `{doc, passes, hypotheses, open_questions}` — the Scientist's lean lab notebook

## Tests

```bash
PYTHONPATH=. python tests/test_smoke.py
```

Validates the inference helpers, the Scientist's modeling helpers, runs one
full Librarian pass against the demo schema, then one Scientist pass on top of
it (no network required).
