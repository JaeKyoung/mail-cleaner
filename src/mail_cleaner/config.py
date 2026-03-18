import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    credentials_path: str
    token_path: str
    scholar_query: str
    max_results: int
    days_back: int
    slack_bot_token: str
    slack_channel: str
    ollama_model: str
    use_summary: bool


def load_config() -> Config:
    """Load configuration from .env (sensitive tokens and file paths)."""
    load_dotenv()
    return Config(
        # From .env (tokens and paths)
        credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"),
        token_path=os.getenv("GMAIL_TOKEN_PATH", "credentials/token.json"),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        # Defaults (overridable via CLI args)
        scholar_query="from:scholaralerts-noreply@google.com",
        max_results=50,
        days_back=7,
        slack_channel="journal-club",
        ollama_model="qwen3:8b",
        use_summary=True,
    )
