# Mail Cleaner

<p align="center">
  <img src="img/B.png" alt="Mail Cleaner">
</p>

A Gmail cleaning bot that processes Google Scholar alert emails — groups papers by date, removes duplicates, and presents a clean digest.

Tested with 50 emails / 304 papers parsed, deduplicated to 204 unique papers across 3 days.

## Features

- **Phase 1** (done): Fetch Scholar alerts → parse papers → deduplicate → console output
- **Phase 2** (done): Send digest to Slack with AI-summarized abstracts (see [Slack setup](doc/slack-setup.md))
- **Phase 2.5** (done): Fetch full abstracts from paper URLs (arXiv, PubMed, generic meta tags)
- **Phase 2.7** (done): Batch-based email processing (`--batches N`)
- **Phase 3** (done): Auto-delete processed emails (enabled by default, skip with `--no-cleanup`)
- **Phase 4** (planned): Paper recommendation DB integration + importance scoring
- **Future** (planned): Interactive Slack bot for on-demand digests (reuses `pipeline.py`)

## Prerequisites

- Python 3.12+
- [pixi](https://pixi.sh) package manager
- Google Cloud project with Gmail API enabled
- [Ollama](https://ollama.ai) with `qwen3:8b` model (for abstract summarization)

## Setup

### 1. Install dependencies

```bash
pixi install
```

### 2. Configure Gmail API credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Gmail API**
4. Navigate to **API & Services** → **OAuth consent screen**
5. Set User type to **External**, fill in app name and email, save
6. Add your Gmail address as a **test user**
7. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
8. Application type: **Desktop application**
9. Download the JSON file and save it:

```bash
mv ~/Downloads/client_secret_*.json credentials/credentials.json
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

### 4. Run

```bash
pixi run run
```

On first run, a browser window opens for Gmail OAuth consent. After granting access, `credentials/token.json` is saved for subsequent runs.

#### CLI Options

All non-sensitive settings can be customized via command-line arguments:

```bash
# Use default settings
pixi run run

# Fetch only recent 10 papers from last 3 days
pixi run run --max-results 10 --days-back 3

# Use openclaw model
pixi run run --model openclaw

# Use raw abstract instead of AI summary
pixi run run --no-summary

# Skip fetching full abstracts (use snippets only)
pixi run run --no-fetch-abstracts

# Process only the latest batch
pixi run run --batches 1

# Print only (skip Slack)
pixi run run --no-slack

# Skip trashing processed emails (cleanup is on by default)
pixi run run --no-cleanup

# Post to different channel
pixi run run --channel research-papers

# Combine options
pixi run run --days-back 7 --batches 2 --no-slack --no-summary
```

To see all available options:
```bash
pixi run run --help
```

## Configuration

### Environment Variables (.env)

Sensitive tokens and file paths are stored in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_CREDENTIALS_PATH` | `credentials/credentials.json` | Path to OAuth credentials |
| `GMAIL_TOKEN_PATH` | `credentials/token.json` | Path to store auth token |
| `SLACK_BOT_TOKEN` | | Slack Bot User OAuth Token ([setup](doc/slack-setup.md)) |

### CLI Options

Non-sensitive settings are configured via command-line arguments (see `pixi run run --help`):

| Option | Default | Description |
|--------|---------|-------------|
| `--max-results` | `200` | Max emails to fetch per run |
| `--days-back` | `7` | How many days back to look |
| `--model` | `qwen3:8b` | Ollama model for abstract summarization |
| `--no-summary` | `false` | Use raw abstract instead of AI summary |
| `--no-fetch-abstracts` | `false` | Skip fetching full abstracts from paper URLs |
| `--batches` | all | Process only the latest N batches |
| `--no-slack` | `false` | Skip sending digest to Slack (print only) |
| `--no-cleanup` | `false` | Skip trashing processed emails after output |
| `--verbose` | `false` | Show details of trashed emails |
| `--channel` | `journal-club` | Slack channel to post digest |
| `--query` | `from:scholaralerts-noreply@google.com` | Gmail search query |

## Project Structure

```
mail-cleaner/
├── src/mail_cleaner/
│   ├── __init__.py
│   ├── main.py           # Entry point — runs the pipeline
│   ├── pipeline.py        # Core pipeline logic (reusable for bot)
│   ├── config.py          # Configuration loading from .env
│   ├── gmail_client.py    # Gmail API authentication + email fetching
│   ├── scholar_parser.py   # Google Scholar HTML email parsing
│   ├── abstract_fetcher.py # Full abstract fetching (arXiv, PubMed, generic)
│   ├── cleanup.py          # Trash processed emails via Gmail API
│   ├── dedup.py           # Date grouping + deduplication
│   ├── models.py          # Data classes (Paper, DailyDigest)
│   ├── output.py          # Console output formatting
│   ├── slack_output.py    # Slack digest output
│   └── summarizer.py      # Abstract summarization via Ollama (qwen3:8b)
├── doc/
│   ├── architecture.md    # Architecture overview
│   ├── setup-guide.md     # Detailed setup instructions
│   └── slack-setup.md     # Slack Bot setup guide
├── img/                   # Images for documentation
├── credentials/           # OAuth credentials (gitignored)
├── pyproject.toml         # Project config + pixi dependencies
├── CLAUDE.md              # AI reference guide
├── .env.example           # Environment variable template
└── README.md
```

## Pipeline

```
Gmail API → list emails → [batch detect → select batches] → full fetch → parse HTML → extract papers → deduplicate → group by date → fetch full abstracts → summarize (Ollama) → output
```

Each module has a single responsibility and a clear public interface:

- `pipeline.run_digest_pipeline()` → orchestrates full pipeline (fetch → parse → dedup → fetch abstracts), designed for reuse by CLI and future bot
- `gmail_client.fetch_scholar_emails()` → `list[dict]` (raw Gmail messages)
- `scholar_parser.parse_email()` → `list[Paper]` (parsed from one email)
- `dedup.group_and_dedup()` → `list[DailyDigest]` (grouped + deduplicated)
- `abstract_fetcher.fetch_full_abstracts()` → `list[Paper]` (with full abstracts from paper URLs)
- `output.print_digest()` → console output
- `summarizer.summarize_abstract()` → 3-bullet summary via Ollama (qwen3:8b)
- `slack_output.send_digest_to_slack()` → Slack channel output (with summaries in thread)

## Known Limitations

- **Abstract fetching coverage**: Full abstract fetching works for arXiv, PubMed, and sites with standard meta tags (`citation_abstract`, `og:description`). Some journal sites may block automated requests or use JavaScript rendering, in which case the original snippet is preserved.

## Scheduling with Cron

To run mail-cleaner automatically every day at 9:00 AM:

1. Open the crontab editor:
   ```bash
   crontab -e
   ```

2. Add the following line:
   ```bash
   0 9 * * * cd /Users/jk_cssb/clawbase/apps/mail-cleaner && /Users/jk_cssb/.pixi/bin/pixi run run >> /tmp/mail-cleaner.log 2>&1
   ```

3. Verify the cron job is registered:
   ```bash
   crontab -l
   ```

Logs are written to `/tmp/mail-cleaner.log`. To disable, remove the line with `crontab -e`.

> **Note**: On macOS, you may need to grant **Full Disk Access** to `cron` (or your terminal) in **System Settings → Privacy & Security** for Gmail token access to work.

## Using as a Submodule (OpenClaw Skill)

This project can be used as a git submodule within a parent repo (e.g., [clawbase](https://github.com/JaeKyoung/clawbase)). In this setup, credentials live **outside** the submodule so it stays clean.

### Directory layout

```
parent-repo/
├── apps/mail-cleaner/              ← this repo (submodule)
├── credentials/mail-cleaner/       ← credentials (gitignored in parent)
│   ├── credentials.json
│   └── token.json
└── skills/mail-cleaner/            ← OpenClaw skill definition
```

### Setup

1. Add as submodule:
   ```bash
   git submodule add https://github.com/JaeKyoung/mail-cleaner.git apps/mail-cleaner
   ```

2. Place Gmail OAuth credentials outside the submodule:
   ```bash
   mkdir -p credentials/mail-cleaner
   cp credentials.json credentials/mail-cleaner/
   ```

3. Set environment variables to point to the external credentials. No `.env` file needed inside the submodule — configure via your parent system (e.g., OpenClaw `openclaw.json`):
   ```
   GMAIL_CREDENTIALS_PATH=/absolute/path/to/credentials/mail-cleaner/credentials.json
   GMAIL_TOKEN_PATH=/absolute/path/to/credentials/mail-cleaner/token.json
   SLACK_BOT_TOKEN=xoxb-...
   ```

   For OpenClaw, set these in `~/.openclaw/openclaw.json`:
   ```json
   {
     "skills": {
       "entries": {
         "mail-cleaner": {
           "enabled": true,
           "env": {
             "SLACK_BOT_TOKEN": "xoxb-...",
             "GMAIL_CREDENTIALS_PATH": "/path/to/credentials/mail-cleaner/credentials.json",
             "GMAIL_TOKEN_PATH": "/path/to/credentials/mail-cleaner/token.json"
           }
         }
       }
     }
   }
   ```

4. Run:
   ```bash
   cd apps/mail-cleaner && pixi install && pixi run run
   ```

`config.py` resolves relative paths against the project root and supports absolute paths from env vars, so both standalone and submodule usage work without code changes.

---

All code in this project was written by [Claude Code](https://claude.com/claude-code) (Anthropic).

