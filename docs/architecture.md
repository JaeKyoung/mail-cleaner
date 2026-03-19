# Architecture

## Overview

LarkLab follows an ETL (Extract-Transform-Load) pipeline architecture. Each stage processes data and passes it to the next.

```
    Extract          Transform                              Load
┌─────────────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐
│ GmailClient │──▶│  Dedup  │──▶│ Abstract │──▶│ Summarize │──▶│  Output  │
│(fetch+parse)│   │ (group) │   │(fetcher) │   │ (Ollama)  │   │ (Slack)  │
└─────────────┘   └─────────┘   └──────────┘   └───────────┘   └──────────┘
```

## Project Structure

```
src/larklab/
├── config.py              # Configuration (credentials from .env)
├── schemas.py              # Data schemas (Paper, DailyDigest)
├── main.py                # CLI entry point (click)
├── pipeline.py            # Pipeline orchestration
│
├── extract/               # Extract — data collection from external sources
│   ├── gmail_client.py    # GmailClient class (auth, fetch, parse, trash)
│   ├── scholar_parser.py  # HTML parsing (called via GmailClient facade)
│   └── abstract_fetcher.py # Fetch full abstracts from paper URLs
│
├── transform/             # Transform — data processing & analysis
│   ├── dedup.py           # Deduplication + grouping by date
│   ├── summarizer.py      # LLM summarization (Ollama)
│   ├── (db.py)            # ← Phase 1: sqlite-vec + embeddings
│   └── (scorer.py)        # ← Phase 4: recommendation scoring
│
└── load/                  # Load — result delivery
    ├── terminal.py        # Console output
    ├── slack.py           # Slack digest posting
    └── (bot.py)           # ← Phase 6: Slack bot
```

Foundational modules (`config`, `schemas`) and orchestration (`main`, `pipeline`) stay at the package root. Domain modules follow the ETL pattern: `extract/` collects raw data, `transform/` processes it, `load/` delivers results.

## Data Flow

1. **Extract** — `GmailClient` authenticates via OAuth2, fetches raw email messages, and parses them into `Paper` objects (delegates to `scholar_parser` internally)
2. **Transform** — `transform/dedup.py` removes duplicate papers (by normalized title) and groups remaining papers by received date
3. **Extract** — `extract/abstract_fetcher.py` visits each paper's URL to retrieve full abstracts (arXiv, PubMed, generic meta tags). Replaces snippet only when fetched abstract is longer; preserves original on failure. Rate-limited with 2s delay and retry on transient errors.
4. **Transform** — `transform/summarizer.py` generates 3-bullet summaries (problem, technical approach, finding) of each paper's abstract using a local LLM (Ollama/qwen3:8b). Summaries are stored in `Paper.summary`.
5. **Load** — `load/terminal.py` prints to console, `load/slack.py` sends formatted digest to Slack (summary + threaded details)

## Module Dependency Graph

```
main.py
  ├── config.py              (no internal deps)
  ├── extract/gmail_client   → config, models (GmailClient: auth, fetch, parse, trash)
  ├── pipeline.py            → config, models, extract/gmail_client, extract/abstract_fetcher,
  │                            transform/dedup, transform/summarizer
  ├── load/terminal.py       → models
  └── load/slack.py          → config, models

schemas.py                    (no internal deps)
```

## Key Design Decisions

### ETL package structure

Modules are grouped into `extract/`, `transform/`, and `load/` following the ETL pattern. This is a natural fit for a batch data pipeline that runs on a cron schedule: extract data from Gmail, transform it (dedup, summarize), and load results to Slack/terminal. Future additions have clear homes (e.g., new crawler → `extract/`, DB → `transform/`, bot → `load/`).

### Configuration separation

Sensitive credentials (OAuth paths, Slack token) are loaded from `.env` via `config.py`. All other settings (days_back, model, channel, etc.) are CLI arguments defined in `main.py` — single source of truth, no duplication.

### Dataclasses over dicts

`Paper` and `DailyDigest` provide type safety and clear contracts between modules. A typo becomes an `AttributeError` instead of a silent `None`.

### Synchronous execution

Gmail API calls are sequential (list → get each message). Async would add complexity for marginal speedup on ~50 emails.

### Parser isolation

Google Scholar's HTML format will change eventually. All parsing logic is isolated in `extract/scholar_parser.py` — a format change is a single-file fix.

## Extension Points

### Completed

| Phase | Modules | Description |
|-------|---------|-------------|
| Slack output | `load/slack.py`, `transform/summarizer.py` | Sends digest with AI summaries to Slack thread |
| Full abstracts | `extract/abstract_fetcher.py` | Fetches full abstracts after dedup, before summarization |
| Email cleanup | `GmailClient.trash_emails()` | Default on (`--no-cleanup` to skip). Uses `Paper.source_email_id` to trash processed emails |

### Planned

- **Paper DB**: `transform/db.py` with `sqlite-vec` for paper storage + vector similarity search
  - Use local embeddings via Ollama (`nomic-embed-text`) — no external APIs
  - `Paper` dataclass should gain an `embedding: list[float] | None` field
  - DB schema: papers table (metadata + embedding), user_interests table (reference embeddings)
  - Keep DB operations in `db.py` only — other modules must not import sqlite directly
- **Similarity Search + Recommendation**: `transform/scorer.py` for importance scoring based on embedding similarity
  - Insert scoring step between `group_and_dedup()` and output
- **Field Classification**: Auto-categorize papers by research area
- **Paper Crawler**: New module in `extract/` to collect papers beyond Scholar alerts
- **Full Paper Summarization**: PDF download + text extraction in `extract/`, full-text mode in `transform/summarizer.py`
- **Slack Bot**: `load/bot.py` that reuses `pipeline.py` for on-demand digests and queries
- **Multi-backend summarization**: Currently Ollama only (`ollama.chat()`). To support other backends (OpenAI, Claude, etc.), consider `litellm` or a provider flag in `transform/summarizer.py`

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching supports arXiv, PubMed, and sites with standard meta tags (`citation_abstract`, `og:description`). Some journal sites may block automated requests or use JavaScript rendering, in which case the original snippet is preserved.
