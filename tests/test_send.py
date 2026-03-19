"""Test sending an email to yourself."""

import base64
from email.mime.text import MIMEText

from larklab.config import load_config
from larklab.gmail_client import get_gmail_service


def main():
    config = load_config()
    service = get_gmail_service(config)

    # Get user's own email address
    profile = service.users().getProfile(userId="me").execute()
    my_email = profile["emailAddress"]
    print(f"Sending test email to: {my_email}")

    # Create a simple test email
    message = MIMEText("This is a test email from mail-cleaner. You can delete this.")
    message["to"] = my_email
    message["from"] = my_email
    message["subject"] = "[mail-cleaner] Test email - please ignore"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    print(f"Sent! Message ID: {result['id']}")
    return result["id"]


if __name__ == "__main__":
    main()
