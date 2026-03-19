---
description: "Session wrap-up: update memory files and write handoff notes for the next session"
user-invocable: true
---

# Pack

Run at the end of a session. Perform the following two steps:

1. **Update memory** (`.claude/memory/`)
   - Add or update memory files if new design decisions, experiment results, or reference info were learned this session
   - Skip if nothing changed

2. **Write handoff** (`.claude/handoff.md`)
   - Current branch
   - Summary of what was done this session
   - Concrete next steps for the next session
   - Open questions or blockers
