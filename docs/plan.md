# LarkLab Development Plan

## Current State

Scholar alerts → parse → dedup → abstract fetch → AI summarize → Slack digest + email cleanup

## Phase 1: Paper DB

Store papers locally with vector embeddings for future search and recommendation.

- [ ] Add `transform/db.py` — sqlite-vec for paper storage and vector search
- [ ] Add Ollama `nomic-embed-text` embedding generation
- [ ] Add `embedding: list[float] | None` field to `Paper` dataclass
- [ ] DB schema: `papers` (metadata + embedding), `user_interests` (reference embeddings)
- [ ] Insert DB save step after digest in pipeline
- [ ] Deduplicate against DB (skip already-stored papers)

## Phase 2: Similarity Search

Find related papers using vector similarity.

- [ ] Add similarity search query to `transform/db.py`
- [ ] CLI command to search papers by keyword/embedding

## Phase 3: Field Classification

Auto-categorize papers by research area.

- [ ] Classify papers into fields using embeddings (clustering or predefined categories)
- [ ] Store field labels in DB
- [ ] Group digest output by field

## Phase 4: Recommendation

Surface relevant papers based on user interests.

- [ ] Add `transform/scorer.py` for importance scoring
- [ ] Manage user interest profiles in `user_interests` table
- [ ] Rank papers by relevance in digest output

## Phase 5: Full Paper Summarization

Summarize based on full paper content, not just abstract.

- [ ] PDF download + text extraction (extract/)
- [ ] Full-text summarization mode in `transform/summarizer.py`
- [ ] CLI option to choose summary source (`--summary-source abstract|full`)
- [ ] Requires larger context model — qwen3:8b may not be sufficient

## Phase 6: Paper Crawler

Collect papers beyond Scholar alerts.

- [ ] New module in `extract/` — scope depends on target sources

## Phase 7: Slack Bot (if needed)

Only relevant after DB + recommendation are in place, and only if interactive queries via Slack become necessary. Current one-way digest delivery may be sufficient.

- [ ] `load/bot.py` that reuses `pipeline.py`
- [ ] Slash commands for search, recommendation queries
