---
name: Database architecture decisions
description: Key design decisions for paper DB — embedding model, MRL, scoring vs filtering, single table
type: project
---

- Embedding model: `qwen3-embedding:8b` (fixed, no model selection option)
- MRL truncation: 4096 → 1024 dimensions (L2 normalized) — saves 4x storage, negligible quality loss
- DB: single `papers` table + `papers_vec` virtual table (sqlite-vec, cosine distance)
- Scholar digest: **scoring only** (top 3 related papers shown), no filtering — user sees all papers
- Filtering reserved for future crawling feature (arxiv/bioarxiv direct fetch)
- CLI commands all `db-*` prefixed: db-add, db-edit, db-delete, db-list, db-search, db-export, db-import, db-rebuild
- `db-add` accepts URL or DOI. Fetch priority: arXiv API → bioRxiv API → HTML crawl → PubMed API → CrossRef API
- `db-add` shows preview before saving, detects near-duplicates (cosine distance < 0.2) with interactive update/new/skip per match
- `db-export` writes individual JSONs to `data/jsons/{id}.json`, `--md` for papers.md (auto-run by pre-commit hook)
- `db-check --refetch` re-fetches from sources and compares with DB
- Authors separator in CLI: pipe (`|`) not comma (shell-safe)
- Science journal: CrossRef returns editor summary, PubMed fallback gets real abstract
- Nature: `#Abs1-content` parser with `<sup>` footnote removal
- bioRxiv: API returns SCPLOW markers + trailing footnotes, both auto-cleaned
- PaperRepository supports context manager (`with`), has `get_by_id()`, uses `INSERT OR IGNORE` for bulk ops

**Why:** User wants to see all Scholar alert papers (never miss any), with similarity as informational context. Filtering will only apply to high-volume crawled sources.
**How to apply:** Don't add filtering to the Scholar digest pipeline. When implementing crawlers, use threshold-based filtering (like prior bot's `any > 0.8` pattern).
