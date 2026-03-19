# Slack Bot Setup

## 1. Create a Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. App Name: `larklab`
4. Select your workspace → **Create App**

## 2. Add Bot Permissions

1. In the left sidebar, go to **OAuth & Permissions**
2. Scroll to **Bot Token Scopes** and add:
   - `chat:write` — Send messages to channels
   - `chat:write.customize` — Customize bot name and icon per message
   - `commands` — Register slash commands (for future use)

## 3. Install to Workspace

1. In the left sidebar, go to **Install App**
2. Click **Install to Workspace**
3. Review and allow the permissions
4. Copy the **Bot User OAuth Token** (`xoxb-...`)

## 4. Configure

Add the token to your `.env` file:

```bash
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=larklab
```

## 5. Invite Bot to Channel

In Slack, open the channel you want to use and type:

```
/invite @larklab
```

## Security

- **Never commit** the bot token to git (`.env` is gitignored)
- If the token is ever exposed, go to **OAuth & Permissions** in the Slack App settings and click **Regenerate** to get a new token
