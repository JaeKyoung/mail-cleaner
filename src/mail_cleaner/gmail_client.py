import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mail_cleaner.config import Config

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


def fetch_scholar_emails(service, config: Config) -> list[dict]:
    """Fetch Google Scholar alert emails from Gmail."""
    query = f"{config.scholar_query} newer_than:{config.days_back}d"

    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=config.max_results)
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
