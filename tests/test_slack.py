"""Test sending a message to Slack."""

import os

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def main():
    load_dotenv()
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL", "mail-cleaner")

    client = WebClient(token=token)

    try:
        result = client.chat_postMessage(
            channel=channel,
            text="Hello from mail-cleaner! This is a test message.",
        )
        print(f"Sent to #{channel}, ts: {result['ts']}")
    except SlackApiError as e:
        print(f"Error: {e.response['error']}")


if __name__ == "__main__":
    main()
