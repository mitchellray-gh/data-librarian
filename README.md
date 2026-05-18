# 📚 Data Librarian + 🔬 Scientist + 📈 Analyst

A perpetually-awake **three-agent** AI system for a Databricks Unity Catalog
schema. The Librarian recursively crawls the catalog and accumulates training,
guidance, inference and pattern notes. The Scientist reads what the Librarian
writes and continuously curates a **lean, evolving lab notebook** focused on
modeling, distributions, candidate targets/features, hypotheses and open
questions. The Analyst then fuses both with an **external consumer-trends
feed** to derive business-relevant insights. All three answer through a sleek
white chat UI backed by a Claude serving endpoint — switch between them with a
persona toggle.

> **Librarian** — confident, assertive, a *touch* smug — but warm. "I have read every table."
> **Scientist** — curious, investigative, hypothesis-driven. "What's the data-generating process here?"
> **Analyst** — pragmatic strategy consultant. "What does this trend mean for revenue next quarter?"

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
- **Business-insights synthesis (Analyst)** — runs as its own background task
  on a slower **two-hour** cadence. Reads both the Librarian's catalog and the
  Scientist's lab notebook, correlates them against an external
  consumer-trends feed (built-in offline-safe fallback, or `CONSUMER_TRENDS_URL`)
  and writes a lean **Analyst Briefing** with portfolio-level pressure
  observations and table-cited business insights.
- **Lean knowledge documents** — Scientist Lab Notebook (`/api/scientist/doc`)
  and Analyst Briefing (`/api/analyst/brief`) are continuously rewritten,
  capped per-section so they stay lean, persist across restarts, and render
  live in the UI.
- **Persona-aware chat** — `POST /api/chat` accepts `persona: "librarian" |
  "scientist" | "analyst"`. Each persona is fed a progressively richer context
  (Librarian alone → + lab notebook → + briefing + trends).
- **Sleek "alive" chat UI** — heartbeat ring, live "currently studying"
  indicator, scrolling activity ticker (science and insight entries styled
  distinctly), expandable Lab Notebook and Analyst Briefing panels, and a
  three-way persona dropdown in the composer.
- **Pluggable endpoints** — Databricks workspace, Claude serving endpoint, and
  optional consumer-trends URL are all set via `.env`. Until configured, the
  app runs end-to-end against a built-in demo schema, a local fallback
  responder, and a curated trends feed.

## Layout

```
app/
  main.py              FastAPI app: /, /api/status, /api/chat, /api/stream (SSE),
                       /api/scientist/doc, /api/analyst/brief
  agent.py             Librarian — recursive live learning agent (background asyncio task)
  scientist.py         Scientist — investigative second-stage agent that writes the lean lab notebook
  analyst.py           Analyst — business-insights agent fusing Librarian + Scientist + consumer trends
  knowledge.py         Persistent knowledge store (tables, patterns, guidance, activity,
                       scientist doc, analyst brief, consumer trends)
  databricks_client.py Databricks SDK wrapper (graceful demo fallback)
  claude_client.py     Claude serving endpoint client + Librarian/Scientist/Analyst prompts
  config.py            .env-driven settings
  static/              index.html, styles.css, app.js  ← the white chat UI
tests/
  test_smoke.py        Inference + Librarian-pass + Scientist-pass + Analyst-pass smoke tests
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env             # leave blank to run against the built-in demo schema + trends
PYTHONPATH=. uvicorn app.main:app --reload
```

Open http://localhost:8000 — all three agents are already awake. Use the
persona dropdown to ask the Librarian, the Scientist, *or* the Analyst.

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
| `ANALYST_INTERVAL_SECONDS` | How often the Analyst re-curates the business briefing (default `7200` — every two hours) |
| `CONSUMER_TRENDS_URL` | Optional JSON feed of consumer trends (`[{title, category, keywords}]`). Empty → built-in feed. |
| `SAMPLE_ROW_LIMIT` | Max rows the agent will sample per table (default `20`) |
| `KNOWLEDGE_PATH` | Where the persistent knowledge JSON lives |

## API

- `GET  /`                    — the chat UI
- `GET  /api/status`          — live snapshot (uptime, librarian/scientist/analyst passes, recent activity, config)
- `POST /api/chat`            — `{message, history, persona}` → `{reply, knowledge_passes, tables_known, persona}`
- `GET  /api/stream`          — Server-Sent Events; one `tick` per second driving the UI's "alive" feel
- `GET  /api/scientist/doc`   — `{doc, passes, hypotheses, open_questions}` — the Scientist's lean lab notebook
- `GET  /api/analyst/brief`   — `{brief, passes, insights, trends}` — the Analyst's lean business briefing

## Tests

```bash
PYTHONPATH=. python tests/test_smoke.py
```

Validates the inference helpers, the Scientist's modeling helpers and the
Analyst's correlation helpers, then runs one full Librarian → Scientist →
Analyst pass against the demo schema (no network required).
