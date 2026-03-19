import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from larklab.config import Config
from larklab.schemas import DailyDigest


def send_digest_to_slack(
    digests: list[DailyDigest],
    config: Config,
    num_emails: int = 0,
    num_parsed: int = 0,
) -> None:
    """Send paper digests to Slack, one message per batch."""
    if not config.slack_bot_token:
        print("Slack bot token not configured, skipping Slack output.")
        return

    client = WebClient(token=config.slack_bot_token)

    for digest in digests:
        _send_batch(client, config.slack_channel, digest)

    total = sum(len(d.papers) for d in digests)
    print(
        f"Sent {len(digests)} batch(es) to "
        f"#{config.slack_channel} ({total} papers total)"
    )


def _send_batch(client: WebClient, channel: str, digest: DailyDigest) -> None:
    """Send a single batch as summary + threaded papers."""
    count = len(digest.papers)
    summary = f"*Scholar Digest — {digest.date}*\n• {count} papers"

    thread_ts = _post(client, channel, summary)
    if not thread_ts:
        return

    for paper in digest.papers:
        authors = ", ".join(paper.authors) if paper.authors else "Unknown"
        text = paper.summary or paper.abstract or ""

        fields = [
            {"title": "Authors", "value": authors, "short": False},
        ]

        attachment = {
            "color": "#CC7D5E",
            "fallback": paper.title,
            "author_name": paper.journal or "Unknown",
            "title": paper.title,
            "title_link": paper.url,
            "text": text,
            "fields": fields,
            "mrkdwn_in": ["text"],
        }
        _post(
            client,
            channel,
            paper.title,
            thread_ts=thread_ts,
            attachments=[attachment],
        )


def _post(
    client: WebClient,
    channel: str,
    text: str,
    thread_ts: str | None = None,
    attachments: list | None = None,
) -> str | None:
    for attempt in range(3):
        try:
            result = client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                attachments=attachments,
                unfurl_links=False,
                unfurl_media=False,
            )
            return result["ts"]
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                retry_after = int(e.response.headers.get("Retry-After", 1))
                print(f"  Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                print(f"Slack error: {e.response['error']}")
                return None
    print("Slack error: rate limit retries exhausted")
    return None
