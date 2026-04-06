# Handoff — 2026-04-06

## Current Branch

`feat/output-json` (pushed, PR pending on GitHub web)

## What Was Done

### Pipeline resilience (merged as #11)
- Added `httpx.ProtocolError` to retry exceptions in abstract fetcher (`RemoteProtocolError` was crashing the pipeline)
- Wrapped per-paper abstract fetch in try/except so one failure doesn't crash all papers
- Added 1s delay between Slack thread messages to prevent rate limiting / "high volume" UI warning
- Fixed date grouping in dedup: now uses local timezone (KST) instead of UTC, fixing emails grouped under wrong date

### `--output-json` option (feat/output-json branch, PR pending)
- Added `--output-json <path>` to digest command for scheduled Claude agent post-processing
- Uses `dataclasses.fields` + `getattr` instead of `asdict` to avoid deep-copying 1024d embeddings
- Datetime fields explicitly serialized to ISO format
- Updated README and docs/architecture.md

### Other
- Added Development section to README (pre-commit install instructions)
- papers.md updated (29 → 35 reference papers)
- Crontab updated: `--days-back 999 --max-results 200 --batches 5`
- pre-commit hook was not installed — now documented and installed

## Next Steps

1. **Merge PR** — `feat/output-json` PR on GitHub web
2. **Set up Claude scheduled agent** — configure to consume `--output-json` output
3. **Code structure refactor** — move `fetch_paper` + helpers from `cli/paper.py` to `extract/`
4. **Crawling** — direct arXiv/bioRxiv fetch with threshold filtering

## Open Questions

- Abstract coverage ceiling: ~33% still snippets due to bot blocking. Semantic Scholar API could help but adds another dependency.
- `fetch_paper` lives in `cli/paper.py` but is pure logic — should move to `extract/` during refactor
