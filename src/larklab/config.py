import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root: mail-cleaner/ (three levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


def _resolve_path(env_var: str, default_relative: str) -> str:
    """Resolve a path from env var. Relative paths are resolved against PROJECT_ROOT."""
    raw = os.getenv(env_var, default_relative)
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str(PROJECT_ROOT / p)


def load_config() -> Config:
    """Load configuration from environment variables (.env file optional)."""
    load_dotenv(PROJECT_ROOT / ".env")
    return Config(
        credentials_path=_resolve_path("GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"),
        token_path=_resolve_path("GMAIL_TOKEN_PATH", "credentials/token.json"),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        scholar_query="from:scholaralerts-noreply@google.com",
        max_results=50,
        days_back=7,
        slack_channel="journal-club",
        ollama_model="qwen3:8b",
        use_summary=True,
    )
