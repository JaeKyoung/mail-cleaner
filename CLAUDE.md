# CLAUDE.md

Instructions for AI assistants working on this project.

## Behavioral Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

From: <https://github.com/forrestchang/andrej-karpathy-skills>

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## 6. Commit Conventions

Follow `.github/git_commit_template.md` for commit messages.

- Format: `<Type>: <Subject>` (e.g., `Feat: Add classifier-free guidance`)
- Types: Feat, Fix, Refactor, Design, Comment, Style, Test, Chore, Init, Rename, Remove
- Subject: Capitalize first letter, imperative mood, no trailing period, max 50 chars
- Body: Wrap at 72 chars, explain WHAT and WHY
- Do NOT add "Co-Authored-By" lines
- Before committing, ensure pre-commit hooks are installed: `pixi run pre-commit install`

## 7. PR Conventions

- User creates PRs on GitHub web, NOT via `gh` CLI
- Provide PR title and body as copy-pasteable code blocks
- PR title follows `<Type>: <Subject>` format
- Always write in English (all files, commit messages, PR descriptions)
- Follow `.github/pull_request_template.md` sections:
  - **Summary**: One-sentence overview
  - **Key Changes**: Bullet list of main changes
  - **Implementation Details**: Architecture/design decisions
  - **Trouble Shooting**: Issues encountered during implementation
  - **Known Issues & Notes**: Caveats, pre-existing issues
  - **Screenshots**: If applicable
  - **Related Issues**: Link related issues

## Project Rules

- All code and documentation in English
- Use `src/` layout — all Python source under `src/mail_cleaner/`
- Use pixi with `pyproject.toml` — do NOT create `requirements.txt`
- Use dataclasses for data transfer between modules
- Each module has one public interface — keep it that way
- `scholar_parser.py` is fragile (depends on Google's HTML format) — isolate all parsing logic there
- "New articles" emails must always be included in summaries — never skip or filter them out
- Summarizer uses Ollama (qwen3:8b) locally — do not call external APIs for summarization
- Gmail `send` scope is intentionally excluded — only `readonly` and `modify` are used
- **Bot reusability**: `pipeline.py` is designed for reuse by future interactive bot — keep it pure and parameterizable
- **Configuration approach**: `.env` for sensitive info only (tokens, credentials); CLI arguments (click) for all other settings
- **Submodule-friendly**: Credentials live outside the repo (absolute paths via env vars). Do not hardcode paths.
- **MCP-ready design**: Keep modules pure and reusable. Any new module should be callable from both CLI (`main.py`) and a future MCP server (`mcp_server.py`) without modification.
- **Embedding/DB**: Use `sqlite-vec` + Ollama local embeddings only. No external vector DB services.

## Adding dependencies

```bash
pixi add <conda-package>
pixi add --pypi <pypi-package>
```

## Running

```bash
pixi run run
```

## Current status

- Phase 1 (done): Gmail fetch → parse → dedup → console output
- Phase 2 (done): Slack digest with AI-summarized abstracts via Ollama
- Phase 2.5 (done): Full abstract fetching from paper URLs (arXiv, PubMed, generic meta tags)
- Phase 2.7 (done): Batch-based email processing — detect batches by 2-hour gap, process latest N only
- Phase 3 (done): Email cleanup — trash processed emails by default (skip with `--no-cleanup`)

## Extension points

- **Phase 4: Vector DB + Scoring** — designed to integrate with MCP server later
  - Add `db.py` with `sqlite-vec` for paper storage + vector similarity search
  - Add `scorer.py` for importance scoring based on embedding similarity
  - Use local embeddings via Ollama (`nomic-embed-text`) — no external APIs
  - `Paper` dataclass should gain an `embedding: list[float] | None` field
  - DB schema: papers table (metadata + embedding), user_interests table (reference embeddings)
  - Insert scoring step between `group_and_dedup()` and output
  - Keep DB operations in `db.py` only — other modules must not import sqlite directly
- **Future: MCP Server** — expose mail-cleaner capabilities as MCP tools
  - Target: OpenClaw and other agents can call paper-search, paper-score, paper-manage
  - Use FastMCP (Python) to stay in the same stack
  - MCP tools: `search_similar_papers(query)`, `score_papers(paper_ids)`, `get_digest(days_back)`
  - MCP server should reuse `pipeline.py` and `db.py` — no duplicated logic
  - Keep as a separate entry point (`mcp_server.py`), not embedded in `main.py`
- **Future: Interactive Bot**: Create `bot.py` that reuses `pipeline.py` for on-demand digests
  - Use `run_digest_pipeline(config, max_results=N, days_back=M)` for custom parameters
  - Bot can call same logic without duplicating code
- **Future: Abstract Caching**: Cache fetched abstracts to avoid re-fetching (integrate with Phase 4 DB)

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching supports arXiv, PubMed, and sites with standard meta tags (`citation_abstract`, `og:description`). Some journal sites may block automated requests or use JavaScript rendering, in which case the original snippet is preserved.

## Key warnings

- `credentials/` is gitignored — never commit OAuth secrets
- `.env` is gitignored — never commit environment variables
- Keep `doc/` and `README.md` updated when making significant changes
