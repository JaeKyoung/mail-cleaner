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
- Use `src/` layout — all Python source under `src/larklab/`
- Use pixi with `pyproject.toml` — do NOT create `requirements.txt`
- Use dataclasses for data transfer between modules
- Each module has one public interface — keep it that way
- `extract/scholar_parser.py` is fragile (depends on Google's HTML format) — isolate all parsing logic there. Called via `GmailClient` facade, not directly.
- "New articles" emails must always be included in summaries — never skip or filter them out
- Summarizer uses Ollama (qwen3:8b) locally — do not call external APIs for summarization
- Gmail `send` scope is intentionally excluded — only `readonly` and `modify` are used
- **Bot reusability**: `pipeline.py` is designed for reuse by future interactive bot — keep it pure and parameterizable
- **Configuration approach**: `.env` for sensitive info only (tokens, credentials); CLI arguments (click) for all other settings
- **Embedding/DB**: Use `sqlite-vec` + Ollama local embeddings only. No external vector DB services.

## Adding dependencies

```bash
pixi add <conda-package>
pixi add --pypi <pypi-package>
```

## Running

```bash
pixi run digest
```


## Key warnings

- `credentials/` is gitignored — never commit OAuth secrets
- `.env` is gitignored — never commit environment variables
- Keep `docs/` and `README.md` updated when making significant changes
