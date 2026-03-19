---
description: "Session start: read handoff notes and memory files to restore context"
user-invocable: true
---

# Unpack

Run at the start of a session. Perform the following steps:

1. **Read handoff** (`.claude/handoff.md`)
   - Understand current branch, what was done last session, and next steps

2. **Read memory files** (`.claude/memory/`)
   - Read `MEMORY.md` index first, then read referenced memory files
   - If `MEMORY.md` doesn't exist, glob `.claude/memory/**/*.md` and read all files

3. **Summarize**
   - Print a brief summary: current branch, last session's work, and next steps
   - Note any open questions or blockers
   - If no handoff or memory files exist, print "Fresh session — no prior context." and skip
