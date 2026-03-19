import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from larklab.config import Config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_service(config: Config):
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(config.token_path):
        creds = Credentials.from_authorized_user_file(config.token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(config.token_path), exist_ok=True)
        with open(config.token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_scholar_emails(
    service,
    config: Config,
    max_results: int | None = None,
    days_back: int | None = None,
) -> list[dict]:
    """Fetch Google Scholar alert emails from Gmail.

    Override config values if parameters provided.
    """
    actual_max = max_results if max_results is not None else config.max_results
    actual_days = days_back if days_back is not None else config.days_back

    query = f"{config.scholar_query} newer_than:{actual_days}d"

    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=actual_max)
        .execute()
    )

    messages = results.get("messages", [])
    if not messages:
        return []

    raw_emails = []
    for msg in messages:
        full_msg = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        raw_emails.append(full_msg)

    return raw_emails
