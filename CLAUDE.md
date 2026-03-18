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

## Extension points

- **Phase 3**: Add `cleanup.py`, use `Paper.source_email_id` to trash processed emails
- **Phase 4**: Add `scorer.py`, `db.py`, insert scoring step between `group_and_dedup()` and output
- **Future: Interactive Bot**: Create `bot.py` that reuses `pipeline.py` for on-demand digests
  - Use `run_digest_pipeline(config, max_results=N, days_back=M)` for custom parameters
  - Bot can call same logic without duplicating code
  - Consider Slack Socket Mode or Events API for implementation
- **Future: Full Abstract Fetching**: Add module to crawl paper URLs for full abstracts
  - Would need site-specific parsers (arXiv, PubMed, journal sites, etc.)
  - Requires rate limiting and error handling
  - Consider caching to avoid re-fetching

## Known Limitations

- **Abstract truncation**: Google Scholar alert emails only include snippets (partial abstracts), not full abstracts. The parser extracts whatever Google provides. To get full abstracts would require crawling individual paper URLs (not currently implemented due to complexity and rate limiting concerns).

## Key warnings

- `credentials/` is gitignored — never commit OAuth secrets
- `.env` is gitignored — never commit environment variables
- Keep `doc/` and `README.md` updated when making significant changes
