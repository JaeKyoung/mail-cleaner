---
name: Next steps and refactoring needs
description: User-identified priorities for upcoming work — digest test, code structure refactor, then crawling
type: project
---

User's next priorities (as of 2026-03-20):

1. **Commit** — large set of uncommitted changes (see handoff). DB is empty — needs `db-import --md` after commit
2. **Test end-to-end** — `db-import --md` to rebuild DB, then `pixi run digest --batches 1 --no-cleanup` to verify
3. **Code structure refactor** — `cli/paper.py` still has fetch functions that should move to `extract/`
   - Consider: `extract/fetchers/` directory with per-source modules
4. **Crawling** — direct arxiv/bioarxiv fetch (like prior bot) with threshold-based filtering
5. **pixi → uv migration** — uv is faster, consider switching later

**Why:** User explicitly said "지금 너무 한 파일에 많은 것들이 들어 있는 경우가 많은데 이를 좀 디렉토리로 세분화해야할 필요를 느끼네" — too much in single files, need directory decomposition.
**How to apply:** Before adding crawling, refactor fetch/parse code into a cleaner structure. The crawling feature will need the same API clients (arXiv, bioRxiv) that `db-add` already uses.
