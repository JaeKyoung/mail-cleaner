# Handoff — 2026-03-20

## Current Branch

`main` (uncommitted changes, DB is empty — needs `db-import --md` after commit)

## What Was Done

### Dataclass split
- `Paper` → `ScholarPaper` (digest, DOI optional) + `Paper` (DB, DOI required)
- `ScholarPaper.to_paper()` for converting to DB Paper
- `Paper.url` is a `@property` derived from `doi`

### DOI-centric DB
- `url` column removed from DB, `doi` is the identifier
- `db-add` normalizes URL input to DOI URL
- `db-edit --url` → `db-edit --doi`

### Unified fetch
- `fetch_paper(doi, url="")` — public, DOI-first. PubMed → arXiv → bioRxiv → CrossRef → HTML
- `_fetch_from_html` parses abstract from soup directly (no redundant API calls)
- `_fetch_from_pubmed` dead `url` param removed
- `_fetch_from_crossref` dead `url` param removed
- `clean_crossref_abstract()` shared helper (no duplicate cleaning logic)

### Digest abstract fetching
- PubMed DOI search → PubMed title search → CrossRef DOI → HTTP crawling
- `extract_doi()` synthesizes arXiv DOI from abs URL (`10.48550/arXiv.{id}`)
- DOI regex strips bioRxiv suffixes (`.full.pdf`, `.full`, `.abstract`)
- `_resolve_url` strips arXiv `.pdf` extension, bioRxiv suffixes
- CrossRef `Accept: application/json` header override (was broken by shared `text/html` client)

### Other
- `--no-summary` → `--summary`, `--no-slack` controls terminal output
- Slack title duplication fixed
- Scholar parser: `get_text(separator=" ")` fixes word concatenation
- Digest papers sorted by top-1 reference
- Clustering tried and removed (too noisy)

### Test results (2 batches, 68 papers)
- 73 full abstracts (67%), 37 snippets (33%)
- Remaining snippets: Springer/Nature/ScienceDirect/ACS bot blocking + PubMed not indexed

## Next Steps

1. **Commit** — split into logical commits
2. **Rebuild DB** — `pixi run db-import --md`
3. **Test digest** — verify arXiv DOI synthesis + CrossRef fallback improved coverage
4. **Code structure refactor** — move `fetch_paper` + helpers from `cli/paper.py` to `extract/`
5. **Crawling** — direct arXiv/bioRxiv fetch with threshold filtering

## Open Questions

- Abstract coverage ceiling: ~33% still snippets due to bot blocking. Semantic Scholar API could help but adds another dependency.
- `fetch_paper` lives in `cli/paper.py` but is pure logic — should move to `extract/` during refactor
