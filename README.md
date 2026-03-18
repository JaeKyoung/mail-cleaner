# Mail Cleaner

<p align="center">
  <img src="img/B.png" alt="Mail Cleaner">
</p>

A Gmail cleaning bot that processes Google Scholar alert emails — groups papers by date, removes duplicates, and presents a clean digest.

Tested with 50 emails / 304 papers parsed, deduplicated to 204 unique papers across 3 days.

## Features

- **Phase 1** (done): Fetch Scholar alerts → parse papers → deduplicate → console output
- **Phase 2** (done): Send digest to Slack with AI-summarized abstracts (see [Slack setup](doc/slack-setup.md))
- **Phase 3** (planned): Auto-delete processed emails
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

# Post to different channel
pixi run run --channel research-papers

# Combine options
pixi run run --max-results 20 --days-back 14 --model openclaw --channel journal-club
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
| `--max-results` | `50` | Max emails to fetch per run |
| `--days-back` | `7` | How many days back to look |
| `--model` | `qwen3:8b` | Ollama model for abstract summarization |
| `--no-summary` | `false` | Use raw abstract instead of AI summary |
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
Gmail API → fetch emails → parse HTML → extract papers → deduplicate → group by date → summarize (Ollama) → output
```

Each module has a single responsibility and a clear public interface:

- `pipeline.run_digest_pipeline()` → orchestrates full pipeline (fetch → parse → dedup), designed for reuse by CLI and future bot
- `gmail_client.fetch_scholar_emails()` → `list[dict]` (raw Gmail messages)
- `scholar_parser.parse_email()` → `list[Paper]` (parsed from one email)
- `dedup.group_and_dedup()` → `list[DailyDigest]` (grouped + deduplicated)
- `output.print_digest()` → console output
- `summarizer.summarize_abstract()` → 3-bullet summary via Ollama (qwen3:8b)
- `slack_output.send_digest_to_slack()` → Slack channel output (with summaries in thread)

## Known Limitations

- **Abstract snippets**: Google Scholar alert emails include only partial abstracts (snippets), not full text. The parser extracts whatever Google provides. Getting full abstracts would require crawling individual paper pages, which is not implemented due to complexity (varying site structures) and rate limiting concerns.

---

All code in this project was written by [Claude Code](https://claude.com/claude-code) (Anthropic).

