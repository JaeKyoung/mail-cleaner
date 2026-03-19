"""Test trashing an email (moves to trash, not permanent delete)."""

import sys

from larklab.config import load_config
from larklab.extract.gmail_client import GmailClient


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_delete.py <message_id>")
        print("  Get the message_id from test_send.py output")
        sys.exit(1)

    message_id = sys.argv[1]

    config = load_config()
    gmail = GmailClient(config)

    # Trash (not permanent delete) — can be recovered from trash
    gmail._service.users().messages().trash(userId="me", id=message_id).execute()
    print(f"Moved to trash: {message_id}")


if __name__ == "__main__":
    main()
