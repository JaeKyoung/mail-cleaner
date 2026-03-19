import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from larklab.config import Config
from larklab.models import DailyDigest, Paper

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    """Gmail API client for fetching and managing emails."""

    def __init__(self, config: Config):
        self._service = _authenticate(config)

    def fetch_emails(
        self,
        query: str,
        max_results: int,
        days_back: int,
    ) -> list[dict]:
        """Fetch full email messages matching query."""
        q = f"{query} newer_than:{days_back}d"
        results = (
            self._service.users()
            .messages()
            .list(userId="me", q=q, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            return []

        return [
            self._service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="full")
            .execute()
            for msg in messages
        ]

    def list_message_ids(
        self, query: str, max_results: int, days_back: int
    ) -> list[str]:
        """List message IDs matching query."""
        q = f"{query} newer_than:{days_back}d"
        results = (
            self._service.users()
            .messages()
            .list(userId="me", q=q, maxResults=max_results)
            .execute()
        )
        return [m["id"] for m in results.get("messages", [])]

    def fetch_internal_dates(self, msg_ids: list[str]) -> list[tuple[str, int]]:
        """Fetch internalDate for each message ID.

        Returns (id, timestamp_ms) pairs.
        """
        pairs = []
        for mid in msg_ids:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=mid, format="minimal")
                .execute()
            )
            pairs.append((mid, int(msg["internalDate"])))
        return pairs

    def fetch_full_messages(self, msg_ids: list[str]) -> list[dict]:
        """Fetch full message content for given IDs."""
        return [
            self._service.users()
            .messages()
            .get(userId="me", id=mid, format="full")
            .execute()
            for mid in msg_ids
        ]

    def parse_emails(self, raw_emails: list[dict]) -> list[Paper]:
        """Parse raw Gmail messages into Paper objects."""
        from larklab.extract.scholar_parser import parse_email

        papers = []
        for email in raw_emails:
            papers.extend(parse_email(email))
        return papers

    def fetch_and_parse(
        self,
        query: str,
        max_results: int,
        days_back: int,
    ) -> tuple[list[Paper], int]:
        """Fetch Scholar alert emails and parse into Papers.

        Returns (papers, num_emails).
        """
        raw_emails = self.fetch_emails(query, max_results, days_back)
        return self.parse_emails(raw_emails), len(raw_emails)

    def trash_emails(
        self,
        digests: list[DailyDigest],
        verbose: bool = False,
    ) -> list[str]:
        """Move processed emails to trash.

        Returns list of trashed message IDs.
        """
        email_ids = {
            p.source_email_id for d in digests for p in d.papers if p.source_email_id
        }

        trashed = []
        for eid in email_ids:
            try:
                if verbose:
                    meta = (
                        self._service.users()
                        .messages()
                        .get(
                            userId="me",
                            id=eid,
                            format="metadata",
                            metadataHeaders=["Subject"],
                        )
                        .execute()
                    )
                    subject = next(
                        (
                            h["value"]
                            for h in meta["payload"]["headers"]
                            if h["name"] == "Subject"
                        ),
                        "(no subject)",
                    )
                    print(f"  Trashing: {subject}")
                self._service.users().messages().trash(userId="me", id=eid).execute()
                trashed.append(eid)
            except Exception as e:
                print(f"  Failed to trash email {eid}: {e}")

        return trashed


def _authenticate(config: Config):
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(config.token_path):
        creds = Credentials.from_authorized_user_file(config.token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.credentials_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(config.token_path), exist_ok=True)
        with open(config.token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)
