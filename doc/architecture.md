# Architecture

## Overview

Mail Cleaner follows a linear pipeline architecture. Each stage processes data and passes it to the next.

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

| Phase | New modules | Integration point |
|-------|-------------|-------------------|
| Phase 2: Slack output (done) | `slack_output.py`, `summarizer.py` | Sends digest with AI summaries to Slack thread |
| Phase 2.5: Full abstracts (done) | `abstract_fetcher.py` | Fetches full abstracts after dedup, before summarization |
| Phase 3: Email cleanup (default on, `--no-cleanup` to skip) | `cleanup.py` | Use `Paper.source_email_id` to delete processed emails |
| Phase 4: Scoring | `scorer.py`, `db.py` | Insert between `group_and_dedup()` and output in `main.py` |
