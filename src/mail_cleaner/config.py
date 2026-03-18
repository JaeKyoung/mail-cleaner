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


def load_config() -> Config:
    load_dotenv()
    return Config(
        credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"),
        token_path=os.getenv("GMAIL_TOKEN_PATH", "credentials/token.json"),
        scholar_query=os.getenv("SCHOLAR_QUERY", "from:scholaralerts-noreply@google.com"),
        max_results=int(os.getenv("MAX_RESULTS", "50")),
        days_back=int(os.getenv("DAYS_BACK", "7")),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        slack_channel=os.getenv("SLACK_CHANNEL", "mail-cleaner"),
    )
