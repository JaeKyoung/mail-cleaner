# Slack Bot Setup

## 1. Create a Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. App Name: `lark`
4. Select your workspace → **Create App**

## 2. Add Bot Permissions

1. In the left sidebar, go to **OAuth & Permissions**
2. Scroll to **Bot Token Scopes** and add:
   - `chat:write` — Send messages to channels
   - `chat:write.customize` — Customize bot name and icon per message
   - `commands` — Register slash commands (for future use)

## 3. Install and Configure

1. In the left sidebar, go to **Install App**
2. Click **Install to Workspace** and allow the permissions
3. Copy the **Bot User OAuth Token** (`xoxb-...`) that appears
4. Add the token to `.env`:

```bash
echo 'SLACK_BOT_TOKEN=xoxb-your-token-here' >> .env
```

The channel is configured via CLI argument: `pixi run digest --channel your-channel`

## 4. Customize Bot Profile (optional)

1. Go to **App Home** in the left sidebar
2. Under **Your App's Presence in Slack**, click **Edit**
3. Set display name and profile photo for the bot

## 5. Invite Bot to Channel

Create `#journal-club` channel (or your preferred channel), then invite the bot:

```
/invite @lark
```

To post to a different channel, use `--channel`: `pixi run digest --channel other-channel`

## Security

- **Never commit** the bot token to git (`.env` is gitignored)
- If the token is ever exposed, go to **OAuth & Permissions** in the Slack App settings and click **Regenerate** to get a new token
