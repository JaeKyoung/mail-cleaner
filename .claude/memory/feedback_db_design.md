---
name: DB design preferences
description: User preferences for database schema simplicity — minimal columns, no status fields, no pending workflow
type: feedback
---

Keep DB schemas minimal — only store what's needed for the use case.
- No status columns; separate tables if state distinction needed (but user ended up removing pending table entirely)
- No created_at, received_at, summary in DB — these are pipeline-time data, not storage concerns
- User prefers to manually add papers via CLI rather than automated pending/approve workflow

**Why:** User questioned every column during design review. Excess columns add complexity without value for the actual use cases (similarity search, recommendation, keyword analysis).
**How to apply:** When adding DB features, start with the minimum schema and let user request additions.
