# LarkLab Development Plan

## Current State

Scholar alerts → parse → dedup → abstract fetch → AI summarize → Slack digest + email cleanup

## Phase 1: Paper DB

Store papers locally with vector embeddings for future search and recommendation.

- [ ] Add `db.py` — sqlite-vec for paper storage and vector search
- [ ] Add Ollama `nomic-embed-text` embedding generation
- [ ] Add `embedding: list[float] | None` field to `Paper` dataclass
- [ ] DB schema: `papers` (metadata + embedding), `user_interests` (reference embeddings)
- [ ] Insert DB save step after digest in pipeline
- [ ] Deduplicate against DB (skip already-stored papers)

## Phase 2: Similarity Search

Find related papers using vector similarity.

- [ ] Add similarity search query to `db.py`
- [ ] CLI command to search papers by keyword/embedding

## Phase 3: Field Classification

Auto-categorize papers by research area.

- [ ] Classify papers into fields using embeddings (clustering or predefined categories)
- [ ] Store field labels in DB
- [ ] Group digest output by field

## Phase 4: Recommendation

Surface relevant papers based on user interests.

- [ ] Add `scorer.py` for importance scoring
- [ ] Manage user interest profiles in `user_interests` table
- [ ] Rank papers by relevance in digest output

## Phase 5: Paper Crawler

Collect papers beyond Scholar alerts.

- [ ] TBD — scope depends on target sources

## Phase 6: Slack Bot (if needed)

Only relevant after DB + recommendation are in place, and only if interactive queries via Slack become necessary. Current one-way digest delivery may be sufficient.

- [ ] `bot.py` that reuses `pipeline.py`
- [ ] Slash commands for search, recommendation queries
