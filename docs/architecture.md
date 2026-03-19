# Architecture

## Overview

LarkLab follows a linear pipeline architecture. Each stage processes data and passes it to the next.

```
┌───────────┐   ┌────────┐   ┌───────┐   ┌───────────┐   ┌───────────┐   ┌────────┐
│ Gmail API │──▶│ Parser │──▶│ Dedup │──▶│  Abstract  │──▶│ Summarize │──▶│ Output │
│ (fetch)   │   │ (HTML) │   │(group)│   │ (fetcher)  │   │ (Ollama)  │   │(Slack) │
└───────────┘   └────────┘   └───────┘   └───────────┘   └───────────┘   └────────┘
```

## Data Flow

1. **Fetch**: `gmail_client.py` authenticates via OAuth2 and fetches raw email messages matching the Scholar alert query
2. **Parse**: `scholar_parser.py` extracts paper metadata (title, authors, journal, abstract, URL) from the HTML body of each email using BeautifulSoup
3. **Dedup**: `dedup.py` removes duplicate papers (by normalized title) and groups remaining papers by received date
4. **Fetch Abstracts**: `abstract_fetcher.py` visits each paper's URL to retrieve full abstracts (arXiv, PubMed, generic meta tags). Replaces snippet only when fetched abstract is longer; preserves original on failure. Rate-limited with 2s delay and retry on transient errors.
5. **Summarize**: `summarizer.py` generates 3-bullet summaries (problem, technical approach, finding) of each paper's abstract using a local LLM (Ollama/qwen3:8b)
6. **Output**: `output.py` prints to console, `slack_output.py` sends formatted digest to Slack (summary + threaded details)

## Module Dependency Graph

```
main.py
  ├── config.py            (no internal deps)
  ├── pipeline.py          → config.py, gmail_client, scholar_parser, dedup, abstract_fetcher
  ├── gmail_client.py      → config.py
  ├── scholar_parser.py    → models.py
  ├── dedup.py             → models.py
  ├── abstract_fetcher.py  → models.py, httpx
  ├── summarizer.py        → models.py, ollama
  ├── output.py            → models.py
  └── slack_output.py      → models.py, config.py, summarizer.py

models.py                  (no internal deps)
```

## Key Design Decisions

### Flat module structure
All modules live directly in `src/mail_cleaner/`. No nested packages — keeps imports simple and navigation easy at this project scale.

### Dataclasses over dicts
`Paper` and `DailyDigest` provide type safety and clear contracts between modules. A typo becomes an `AttributeError` instead of a silent `None`.

### Synchronous execution
Gmail API calls are sequential (list → get each message). Async would add complexity for marginal speedup on ~50 emails.

### Parser isolation
Google Scholar's HTML format will change eventually. All parsing logic is isolated in `scholar_parser.py` — a format change is a single-file fix.

## Extension Points

### Completed

| Phase | Modules | Description |
|-------|---------|-------------|
| Slack output | `slack_output.py`, `summarizer.py` | Sends digest with AI summaries to Slack thread |
| Full abstracts | `abstract_fetcher.py` | Fetches full abstracts after dedup, before summarization |
| Email cleanup | `cleanup.py` | Default on (`--no-cleanup` to skip). Uses `Paper.source_email_id` to trash processed emails |

### Planned

- **Paper DB**: `db.py` with `sqlite-vec` for paper storage + vector similarity search
  - Use local embeddings via Ollama (`nomic-embed-text`) — no external APIs
  - `Paper` dataclass should gain an `embedding: list[float] | None` field
  - DB schema: papers table (metadata + embedding), user_interests table (reference embeddings)
  - Keep DB operations in `db.py` only — other modules must not import sqlite directly
- **Similarity Search + Recommendation**: `scorer.py` for importance scoring based on embedding similarity
  - Insert scoring step between `group_and_dedup()` and output
- **Field Classification**: Auto-categorize papers by research area
- **Paper Crawler**: Collect papers beyond Scholar alerts
- **Slack Bot**: `bot.py` that reuses `pipeline.py` for on-demand digests and queries
- **Multi-backend summarization**: Currently Ollama only (`ollama.chat()`). To support other backends (OpenAI, Claude, etc.), consider `litellm` or a provider flag in `summarizer.py`

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching supports arXiv, PubMed, and sites with standard meta tags (`citation_abstract`, `og:description`). Some journal sites may block automated requests or use JavaScript rendering, in which case the original snippet is preserved.
