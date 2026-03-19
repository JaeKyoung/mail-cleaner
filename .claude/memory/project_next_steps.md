---
name: Next steps and refactoring needs
description: User-identified priorities for upcoming work — digest test, code structure refactor, then crawling
type: project
---

User's next priorities (as of 2026-03-20):

1. **Test digest with DB** — `pixi run digest` with 28 reference papers, verify similarity scoring output in terminal + Slack
2. **Clustering** — group papers by research field using embeddings (deferred, not urgent)
3. **Code structure refactor** — user feels parsing logic is scattered across too many places:
   - `cli/paper.py` has 5 fetch functions (arXiv, bioRxiv, PubMed, CrossRef, HTML crawl) that should probably be in `extract/`
   - `extract/abstract_fetcher.py` handles abstract parsing for digest pipeline
   - These two systems (CLI fetch vs digest fetch) share some logic but are separate
   - Consider: `extract/fetchers/` directory with per-source modules
4. **Crawling** — direct arxiv/bioarxiv fetch (like prior bot) with threshold-based filtering

**Why:** User explicitly said "지금 너무 한 파일에 많은 것들이 들어 있는 경우가 많은데 이를 좀 디렉토리로 세분화해야할 필요를 느끼네" — too much in single files, need directory decomposition.
**How to apply:** Before adding crawling, refactor fetch/parse code into a cleaner structure. The crawling feature will need the same API clients (arXiv, bioRxiv) that `db-add` already uses.
