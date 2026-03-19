# Handoff — 2026-03-20

## Current Branch

`main` (uncommitted changes — database module, CLI, code quality refactor)

## What Was Done

### Database module (`database/`)
- `embedder.py` — `qwen3-embedding:8b`, MRL 4096→1024d, cosine distance
- `repository.py` — PaperRepository with context manager, `get_by_id()`, `INSERT OR IGNORE` bulk ops, SQL gap-finding, cosine distance in vec0

### CLI (`cli/`)
- Split into `common.py`, `digest.py`, `paper.py`, `io.py`
- All DB commands `db-*` prefixed: add, edit, delete, check, list, search, export, import, rebuild
- `-h` flag support via shared CONTEXT_SETTINGS
- `db-add`: accepts URL or DOI, multi-source fetch (arXiv API → bioRxiv API → HTML → PubMed API → CrossRef), preview + confirmation, duplicate detection
- `db-export`: individual JSONs (`data/jsons/{id}.json`), `--md` for papers.md, `--query` filter
- `db-check --refetch`: re-fetches and compares with DB
- `db-search`: keyword + journal filter + embedding similarity

### Multi-source paper fetching (`cli/paper.py`)
- arXiv: `arxiv` library API
- bioRxiv/medRxiv: REST API with SCPLOW/footnote cleanup
- Nature: `#Abs1-content` parser with `<sup>` removal
- PubMed: E-utilities API (DOI → PMID → metadata), journal tag fix (`journal > title`)
- CrossRef: fallback with JATS cleanup + editor initials removal
- General HTML: `citation_*` meta tags + abstract_fetcher

### Code quality (simplify review)
- `_make_paper()` factory, `_format_authors()` helper (6x dedup)
- Context manager on all repo usage (no more leaked connections)
- `get_by_id()` replaces full table scan in edit/delete
- `save_many()` uses `INSERT OR IGNORE` + single commit
- `_next_id()` via SQL self-join instead of Python set scan
- PubMed journal bug fixed (`soup.find("journal").find("title")`)
- Module-level `import re`, `import warnings`

### Pipeline
- Similarity scoring (top 3 references) on all digest papers, no filtering
- Cosine distance metric in sqlite-vec

### Docs
- README, CLAUDE.md, architecture.md, plan.md all updated
- Pre-commit hook generates `data/papers.md`

### DB state
- 28 reference papers (protein structure, design, language models, PPI)
- Sources: Nature, Science, arXiv, bioRxiv, NAR, Cell Systems, PNAS, Nature Methods, Nature Biotech, Nature Micro

## Next Steps

1. **Test digest**: `pixi run digest --batches 1 --no-slack` — verify similarity scoring with 28 references
2. **Commit**: Split into logical commits (database module, CLI refactor, code quality, docs)
3. **Refactor fetch logic**: `cli/paper.py` has 5 fetch functions that should move to `extract/` — share with future crawling
4. **Crawling**: Direct arXiv/bioRxiv fetch with threshold-based filtering (Phase 6)
5. **Clustering**: Group papers by field using embeddings (deferred)

## Open Questions
- Fetch logic location: `cli/paper.py` vs `extract/fetchers/` — user wants to reorganize before crawling
- Crawling threshold: 0.8 from old bot, needs validation with qwen3-embedding + cosine distance
- Science journal abstracts: PubMed fallback works but adds latency (2 API calls per paper)
