# LarkLab

<p align="center">
  <img src="img/image.png" alt="LarkLab">
</p>

A personal research assistant that collects, organizes, and recommends papers.

## What LarkLab does

1. **Collect** — Gather papers from Google Scholar alerts (and future crawlers)
2. **Store** — Save to local DB with vector embeddings for similarity search
3. **Organize** — Classify papers by research field, deduplicate
4. **Recommend** — Score and surface relevant papers based on your interests
5. **Deliver** — Send daily digests to Slack with AI-summarized abstracts

## Roadmap

- **Scholar Digest** (done): Gmail fetch → parse → dedup → abstract summarization → Slack digest
- **Email Cleanup** (done): Auto-trash processed emails after digest
- **Paper DB** (done): Local storage with `sqlite-vec` + Ollama embeddings (`qwen3-embedding:8b`, MRL 1024d)
- **Similarity Search** (done): Score digest papers by vector similarity to reference papers (top 3 shown)
- **Field Classification** (planned): Auto-categorize papers by research area
- **Recommendation** (planned): Importance scoring based on user interests
- **Full Paper Summarization** (planned): Summarize based on full paper content, not just abstract
- **Paper Crawler** (planned): Collect papers beyond Scholar alerts
- **Slack Bot** (planned): On-demand queries and digests via Slack

## Prerequisites

- Python 3.12+
- [pixi](https://pixi.sh) package manager
- Google Cloud project with Gmail API enabled
- [Ollama](https://ollama.ai) with `qwen3:8b` (summarization) and `qwen3-embedding:8b` (embeddings)

## Setup

### 1. Configure Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Gmail API**: Go to **API & Services** → **Library**, search "Gmail API", click it, then click **Enable**
4. Navigate to **API & Services** → **OAuth consent screen**
5. Set User type to **External**, fill in app name and email, save
6. Add your Gmail address as a **test user**
7. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
8. Application type: **Desktop application**
9. Download the JSON file
10. (Optional) Move it to the project for convenience — you can also set a custom path via `GMAIL_CREDENTIALS_PATH` in `.env`:

```bash
mv ~/Downloads/client_secret_*.json credentials/credentials.json
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

### 3. Install dependencies

```bash
pixi install
```

### 4. Run

```bash
pixi run digest
```

On first run, a browser window opens for Gmail OAuth consent. Gmail scopes (`readonly`, `modify`) are requested automatically by the code — no manual scope configuration needed in Google Cloud Console. After granting access, `credentials/token.json` is saved for subsequent runs.

#### CLI Commands

```bash
# --- Digest ---
pixi run digest                          # Full pipeline: fetch → summarize → score → Slack
pixi run digest --batches 1 --no-slack   # Process latest batch, print only
pixi run digest --no-summary             # Use raw abstract instead of AI summary
pixi run digest --no-fetch-abstracts     # Use snippets only
pixi run digest --no-cleanup             # Skip trashing processed emails

# --- Paper DB ---
pixi run db-add <url>                    # Add paper by URL (arXiv, Nature, bioRxiv, ...)
pixi run db-add <doi>                    # Add paper by DOI (via PubMed → CrossRef)
pixi run db-add <url> --title "..." --authors "A|B" --journal "Nature" --abstract "..."
pixi run db-edit <id> --journal "Nature" # Edit existing paper fields
pixi run db-delete <id>                  # Delete a paper
pixi run db-list                         # List reference papers
pixi run db-search "AlphaFold"           # Search by keyword + embedding similarity
pixi run db-search --journal "Science"   # Search by journal only
pixi run db-search "protein" --journal "Nature"  # Combine keyword + journal
pixi run db-check                        # Check papers for missing fields
pixi run db-check --refetch              # Re-fetch from URLs and compare
pixi run db-export                       # Export papers to data/jsons/{id}.json
pixi run db-export --md                  # Export as Markdown (data/papers.md)
pixi run db-export --query "AlphaFold"   # Export matching papers only
pixi run db-import                       # Import from data/jsons/ (replaces DB)
pixi run db-import --input file.json     # Import from single JSON file
pixi run db-rebuild                      # Re-generate all embeddings
```

To see all available options:
```bash
pixi run larklab --help
pixi run digest --help
```

## Configuration

Sensitive tokens and file paths are stored in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_CREDENTIALS_PATH` | `credentials/credentials.json` | Path to OAuth credentials |
| `GMAIL_TOKEN_PATH` | `credentials/token.json` | Path to store auth token |
| `SLACK_BOT_TOKEN` | | Slack Bot User OAuth Token ([setup](docs/slack-setup.md)) |

## Example Output

### Terminal

```
Fetching Scholar emails from the last 7 days...
Found 10 emails, detecting batches...
Found 2 batches: Batch 1 (6 emails, 03/19 07:16) | Batch 2 (4 emails, 03/17 08:30)
Processing 10 emails.
Parsed 25 papers total.

--- 2026-03-18 (15 papers) ---
  1. Paper Title Here
     Authors: A Author, B Author
     Journal: Nature, 2026
     Abstract: Lorem ipsum dolor sit amet...
  ...

Sent 2 batch(es) to #journal-club (25 papers total)
Trashed 10 processed emails.
```

### Slack

Each batch is posted as a separate message with threaded paper cards:

```
*Scholar Digest — 2026-03-18*
• 15 papers
  ┃ Nature, 2026
  ┃ Paper Title Here
  ┃ Lorem ipsum dolor sit amet, consectetur adipiscing elit...
  ┃ Authors: A Author, B Author

  ┃ Cell, 2026
  ┃ Another Paper Title
  ┃ Sed do eiusmod tempor incididunt ut labore et dolore...
  ┃ Authors: C Author, D Author
```

## Architecture

The project follows an ETL (Extract-Transform-Load) pipeline:

```
Gmail API → batch detect → fetch → parse → dedup → abstract fetch → summarize
  → embed → similarity scoring (top 3) → Slack
```

- **extract/** — `GmailClient` (auth, fetch, parse, trash), `abstract_fetcher` (full abstract crawling)
- **transform/** — `dedup` (deduplication + grouping), `summarizer` (LLM summarization via Ollama)
- **database/** — `embedder` (Ollama embeddings, MRL truncation), `repository` (sqlite-vec CRUD + similarity search)
- **load/** — `terminal` (console output), `slack` (Slack digest posting)
- **cli/** — `digest.py` (digest command), `paper.py` (add/edit/list), `io.py` (export/import/rebuild)
- **root** — `pipeline.py` (orchestration), `config.py` (credentials from .env), `schemas.py` (data schemas), `main.py` (entry point)

See [docs/architecture.md](docs/architecture.md) for details.

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching works for arXiv, PubMed, Nature, and sites with standard meta tags (`citation_abstract`, `og:description`). Some journal sites may block automated requests or use JavaScript rendering, in which case the original snippet is preserved.

## Usage

### Scheduling with Cron

To run larklab automatically every day at 9:00 AM:

1. Open the crontab editor:
   ```bash
   crontab -e
   ```

2. Add the following line:
   ```bash
   0 9 * * * cd /Users/jk_cssb/clawbase/apps/larklab && /Users/jk_cssb/.pixi/bin/pixi run digest >> /tmp/larklab.log 2>&1
   ```

3. Verify the cron job is registered:
   ```bash
   crontab -l
   ```

Logs are written to `/tmp/larklab.log`. To disable, remove the line with `crontab -e`.

> **Note**: On macOS, you may need to grant **Full Disk Access** to `cron` (or your terminal) in **System Settings → Privacy & Security** for Gmail token access to work.

### Slack Bot

See [docs/slack-setup.md](docs/slack-setup.md) for bot setup.

---

All code in this project was written by [Claude Code](https://claude.com/claude-code) (Anthropic).

