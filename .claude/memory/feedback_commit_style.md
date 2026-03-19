---
name: Commit and PR conventions
description: User enforces strict commit template and PR conventions — always check template before committing
type: feedback
---

Always follow `.github/git_commit_template.md` format exactly.
- `<Type>: <Subject>` — max 50 chars, imperative mood, no period
- Do NOT add Co-Authored-By lines
- If changes are large, split into multiple focused commits
- User creates PRs on GitHub web — provide title and body as copy-pasteable code blocks

**Why:** User rejected a commit that didn't follow the template and asked to split large changes.
**How to apply:** Always read the template before committing. When in doubt, split.
