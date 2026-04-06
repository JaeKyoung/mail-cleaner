# Architecture

## Overview

LarkLab follows an ETL (Extract-Transform-Load) pipeline architecture. Each stage processes data and passes it to the next.

```
    Extract          Transform                              Database              Load
┌─────────────┐   ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌───────────┐   ┌─────────────┐
│ GmailClient │──▶│  Dedup  │──▶│ Abstract │──▶│ Summarize │──▶│ Embed +   │──▶│   Output    │
│(fetch+parse)│   │ (group) │   │(fetcher) │   │ (Ollama)  │   │ Filter DB │   │(Slack/JSON) │
└─────────────┘   └─────────┘   └──────────┘   └───────────┘   └───────────┘   └─────────────┘
```

## Project Structure

```
src/larklab/
├── config.py              # Configuration (credentials from .env)
├── schemas.py             # Data schemas (ScholarPaper, Paper, DailyDigest)
├── main.py                # Entry point (delegates to cli/)
├── pipeline.py            # Pipeline orchestration
│
├── cli/                   # CLI commands (click group)
│   ├── __init__.py        # CLI group definition + command registration
│   ├── digest.py          # digest command
│   ├── paper.py           # db-add, db-edit, db-delete, db-list, db-search
│   └── io.py              # db-export, db-import, db-rebuild
│
├── extract/               # Extract — data collection from external sources
│   ├── gmail_client.py    # GmailClient class (auth, fetch, parse, trash)
│   ├── scholar_parser.py  # HTML parsing (called via GmailClient facade)
│   └── abstract_fetcher.py # Fetch full abstracts + DOI (PubMed API → HTTP fallback), extract_doi utility
│
├── transform/             # Transform — data processing & analysis
│   ├── dedup.py           # Deduplication + grouping by date
│   ├── summarizer.py      # LLM summarization (Ollama)
│   └── (scorer.py)        # ← planned: recommendation scoring
│
├── database/              # Database — paper storage & similarity search
│   ├── embedder.py        # Ollama embeddings (qwen3-embedding:8b, MRL 1024d)
│   └── repository.py      # PaperRepository (sqlite-vec CRUD + vector search, DOI column)
│
└── load/                  # Load — result delivery
    ├── terminal.py        # Console output
    ├── slack.py           # Slack digest posting
    └── (bot.py)           # ← planned: Slack bot
```

Foundational modules (`config`, `schemas`) and orchestration (`main`, `pipeline`) stay at the package root. CLI commands are split by domain in `cli/`. Domain modules follow the ETL pattern: `extract/` collects raw data, `transform/` processes it, `load/` delivers results.

## Data Flow

1. **Extract** — `GmailClient` authenticates via OAuth2, fetches raw email messages, and parses them into `ScholarPaper` objects (delegates to `scholar_parser` internally)
2. **Transform** — `transform/dedup.py` removes duplicate papers (by normalized title) and groups remaining papers by received date
3. **Extract** — `extract/abstract_fetcher.py` fetches full abstracts via PubMed E-utilities API first (title search), then falls back to HTTP crawling (arXiv, Nature, generic meta tags). Replaces snippet only when fetched abstract is longer; preserves original on failure. HTTP fallback is rate-limited with 2s delay and retry on transient errors.
4. **Transform** — `transform/summarizer.py` generates 3-bullet summaries (problem, technical approach, finding) of each paper's abstract using a local LLM (Ollama/qwen3:8b). Summaries are stored in `ScholarPaper.summary`.
5. **Database** — `database/embedder.py` generates embeddings for each paper (title + abstract). `database/repository.py` compares against reference papers via `sqlite-vec` cosine distance. Each paper gets a `similar_papers` list with the top 3 closest references and their similarity scores. All papers pass through to output — no filtering. If no reference papers exist, scoring is skipped. Papers are sorted by top-1 reference so related papers appear adjacent.
6. **Load** — `load/terminal.py` prints to console, `load/slack.py` sends formatted digest to Slack (summary + threaded details). `--output-json` exports the full digest as JSON for downstream automation (e.g., Claude Code scheduled agents)

## Module Dependency Graph

```
main.py
  ├── config.py              (no internal deps)
  ├── extract/gmail_client   → config, schemas
  ├── database/embedder      → schemas (Ollama embedding generation)
  ├── database/repository    → schemas, database/embedder (sqlite-vec CRUD)
  ├── pipeline.py            → config, schemas, extract/*, transform/*, database/*
  ├── load/terminal.py       → schemas
  └── load/slack.py          → config, schemas

schemas.py                    (no internal deps)
```

## Key Design Decisions

### ETL package structure

Modules are grouped into `extract/`, `transform/`, and `load/` following the ETL pattern. This is a natural fit for a batch data pipeline that runs on a cron schedule: extract data from Gmail, transform it (dedup, summarize), and load results to Slack/terminal. Future additions have clear homes (e.g., new crawler → `extract/`, DB → `transform/`, bot → `load/`).

### Configuration separation

Sensitive credentials (OAuth paths, Slack token) are loaded from `.env` via `config.py`. All other settings (days_back, model, channel, etc.) are CLI arguments defined in `main.py` — single source of truth, no duplication.

### Dataclasses over dicts

`ScholarPaper` (digest pipeline, DOI optional), `Paper` (DB storage, DOI required), and `DailyDigest` provide type safety and clear contracts between modules. `ScholarPaper.to_paper()` converts for DB storage.

### Synchronous execution

Gmail API calls are sequential (list → get each message). Async would add complexity for marginal speedup on ~50 emails.

### Parser isolation

Google Scholar's HTML format will change eventually. All parsing logic is isolated in `extract/scholar_parser.py` — a format change is a single-file fix.

## Extension Points

### Completed

| Phase | Modules | Description |
|-------|---------|-------------|
| Slack output | `load/slack.py`, `transform/summarizer.py` | Sends digest with AI summaries to Slack thread |
| Full abstracts | `extract/abstract_fetcher.py` | Fetches full abstracts via PubMed API (primary) with HTTP crawling fallback (arXiv, Nature, generic meta tags) |
| Email cleanup | `GmailClient.trash_emails()` | Default on (`--no-cleanup` to skip). Uses `ScholarPaper.source_email_id` to trash processed emails |
| Paper DB | `database/repository.py`, `database/embedder.py` | sqlite-vec storage with `qwen3-embedding:8b` (MRL 1024d). Single `papers` table for reference papers |
| Similarity scoring | `pipeline.py` | Embeds digest papers, scores against references (top 3), sorts by top-1 reference for adjacency |
| JSON export | `cli/digest.py` | `--output-json` saves digest results as JSON for scheduled agent post-processing |
| Duplicate detection | `repository.py`, `cli/paper.py` | `db-add` detects near-duplicates by embedding similarity (cosine distance < 0.2). Prompts per match: update/new/skip. Shows preview before saving |
| Multi-source fetch | `cli/paper.py` | `db-add` fetches metadata: PubMed (DOI) → arXiv API → bioRxiv API → CrossRef (DOI) → HTML crawl (last resort). Accepts URL or DOI |

### Planned

- **Recommendation Scoring**: `transform/scorer.py` for importance scoring beyond binary similarity threshold
- **Field Classification**: Auto-categorize papers by research area
- **Paper Crawler**: New module in `extract/` to collect papers beyond Scholar alerts
- **Full Paper Summarization**: PDF download + text extraction in `extract/`, full-text mode in `transform/summarizer.py`
- **Slack Bot**: `load/bot.py` that reuses `pipeline.py` for on-demand digests and queries
- **Multi-backend summarization**: Currently Ollama only (`ollama.chat()`). To support other backends (OpenAI, Claude, etc.), consider `litellm` or a provider flag in `transform/summarizer.py`

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching uses PubMed E-utilities API first (title search), then falls back to HTTP crawling (arXiv, Nature, generic meta tags). Papers not indexed in PubMed and hosted on JS-rendered sites may retain the original snippet.
