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
- **Paper DB** (planned): Local storage with `sqlite-vec` + Ollama embeddings
- **Similarity Search** (planned): Find related papers by vector similarity
- **Field Classification** (planned): Auto-categorize papers by research area
- **Recommendation** (planned): Importance scoring based on user interests
- **Full Paper Summarization** (planned): Summarize based on full paper content, not just abstract
- **Paper Crawler** (planned): Collect papers beyond Scholar alerts
- **Slack Bot** (planned): On-demand queries and digests via Slack

## Prerequisites

- Python 3.12+
- [pixi](https://pixi.sh) package manager
- Google Cloud project with Gmail API enabled
- [Ollama](https://ollama.ai) with `qwen3:8b` model (for abstract summarization)

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

#### CLI Options

All non-sensitive settings can be customized via command-line arguments:

```bash
# Use default settings
pixi run digest

# Fetch only recent 10 papers from last 3 days
pixi run digest --max-results 10 --days-back 3

# Use a different Ollama model (default: qwen3:8b)
pixi run digest --model gemma2:9b

# Use raw abstract instead of AI summary
pixi run digest --no-summary

# Skip fetching full abstracts (use snippets only)
pixi run digest --no-fetch-abstracts

# Process only the latest batch
pixi run digest --batches 1

# Print only (skip Slack)
pixi run digest --no-slack

# Skip trashing processed emails (cleanup is on by default)
pixi run digest --no-cleanup

# Post to different channel
pixi run digest --channel research-papers

# Combine options
pixi run digest --days-back 7 --batches 2 --no-slack --no-summary
```

To see all available options:
```bash
pixi run digest --help
```

## Configuration

Sensitive tokens and file paths are stored in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_CREDENTIALS_PATH` | `credentials/credentials.json` | Path to OAuth credentials |
| `GMAIL_TOKEN_PATH` | `credentials/token.json` | Path to store auth token |
| `SLACK_BOT_TOKEN` | | Slack Bot User OAuth Token ([setup](docs/slack-setup.md)) |

## Pipeline

```
Gmail API
→ list emails
→ [batch detect → select batches]
→ full fetch
→ parse HTML
→ extract papers
→ deduplicate
→ group by date
→ fetch full abstracts
→ summarize (Ollama)
→ Slack digest
```

The project follows an ETL (Extract-Transform-Load) structure:

- **extract/** — `GmailClient` (auth, fetch, parse, trash), `abstract_fetcher` (full abstract crawling)
- **transform/** — `dedup` (deduplication + grouping), `summarizer` (LLM summarization via Ollama)
- **load/** — `terminal` (console output), `slack` (Slack digest posting)
- **root** — `pipeline.py` (orchestration), `config.py` (credentials from .env), `models.py` (dataclasses), `main.py` (CLI)

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching works for arXiv, PubMed, and sites with standard meta tags (`citation_abstract`, `og:description`). Some journal sites may block automated requests or use JavaScript rendering, in which case the original snippet is preserved.

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

TODO

---

All code in this project was written by [Claude Code](https://claude.com/claude-code) (Anthropic).

