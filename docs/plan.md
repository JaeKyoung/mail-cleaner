# LarkLab Development Plan

## Current State

Scholar alerts → parse → dedup → abstract fetch → AI summarize → embed → similarity scoring (top 3) → Slack digest + email cleanup

## Phase 1: Paper DB (done)

Store papers locally with vector embeddings for search and recommendation.

- [x] Add `database/` module — `repository.py` (sqlite-vec CRUD), `embedder.py` (Ollama embeddings)
- [x] Embedding: `qwen3-embedding:8b` with MRL truncation to 1024d
- [x] Add `embedding`, `similar_papers` fields to `Paper` dataclass
- [x] DB schema: `papers` (reference papers), `papers_vec` (embeddings)
- [x] CLI: `db-add`, `db-edit`, `db-delete`, `db-list`, `db-search`, `db-export`, `db-import`, `db-rebuild`

## Phase 2: Similarity Scoring (done)

Score digest papers by vector similarity to reference papers.

- [x] Embed each digest paper and compute cosine distance to references
- [x] Display top 3 related reference papers with similarity scores (terminal + Slack)
- [x] No filtering — all papers shown, scoring is informational

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
