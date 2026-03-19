# Setup Guide

## Prerequisites

- macOS / Linux
- Python 3.12+
- [pixi](https://pixi.sh) — install with: `curl -fsSL https://pixi.sh/install.sh | bash`
- [Ollama](https://ollama.ai) — for local LLM summarization
- A Google account with Gmail

## Step 1: Clone and Install

```bash
git clone https://github.com/JaeKyoung/larklab.git
cd larklab
pixi install
```

## Step 2: Google Cloud Setup

### Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it (e.g., "larklab") and create

### Enable Gmail API

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click **Enable**

### Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. If prompted, configure the OAuth consent screen:
   - User type: **External** (or Internal if using Google Workspace)
   - App name: "larklab"
   - Add your email as a test user
4. Application type: **Desktop application**
5. Download the JSON file
6. Save it as `credentials/credentials.json` in the project root

## Step 3: Install Ollama Model

```bash
ollama pull qwen3:8b
```

This model is used to summarize paper abstracts locally.

## Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to customize settings if needed. Defaults work fine for most users.

## Step 5: Set Up Slack (Optional)

See [slack-setup.md](slack-setup.md) for Slack Bot configuration.

## Step 6: First Run

```bash
pixi run digest
```

A browser window will open asking you to grant Gmail read access. After consenting, a `credentials/token.json` file is created automatically for future runs.

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Make sure you added your Google account as a test user in the OAuth consent screen

### "File not found: credentials.json"
- Verify the file is saved at `credentials/credentials.json`
- Check that `GMAIL_CREDENTIALS_PATH` in `.env` matches the actual path

### No emails found
- Check your Gmail — do you actually receive Google Scholar alerts?
- Try increasing `DAYS_BACK` in `.env`
- Verify the sender address matches `SCHOLAR_QUERY` in `.env`
