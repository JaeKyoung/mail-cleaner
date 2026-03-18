from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from mail_cleaner.config import Config
from mail_cleaner.models import DailyDigest
from mail_cleaner.summarizer import summarize_abstract


def send_digest_to_slack(
    digests: list[DailyDigest],
    config: Config,
    num_emails: int = 0,
    num_parsed: int = 0,
) -> None:
    """Send the paper digest to Slack as a single summary + threaded details."""
    if not config.slack_bot_token:
        print("Slack bot token not configured, skipping Slack output.")
        return

    client = WebClient(token=config.slack_bot_token)
    total = sum(len(d.papers) for d in digests)

    # Date range
    all_dates = [d.date for d in digests]
    oldest = min(all_dates)
    newest = max(all_dates)

    # Build summary message
    summary = f"*Google Scholar Digest*\n"
    summary += f"• Period: {oldest} ~ {newest}\n"
    summary += f"• {num_emails} emails → {num_parsed} papers → {total} after dedup"

    # Post summary to channel
    thread_ts = _post(client, config.slack_channel, summary)
    if not thread_ts:
        return

    # Post each paper as a thread reply with blocks
    for digest in digests:
        for i, paper in enumerate(digest.papers):
            print(f"  Summarizing paper {i + 1}/{len(digest.papers)}...")
            authors = ", ".join(paper.authors) if paper.authors else "Unknown"
            summary_text = summarize_abstract(paper)

            title_line = f"<{paper.url}|*{paper.title}*>"
            meta_parts = [authors]
            if paper.journal:
                meta_parts.append(f"_{paper.journal}_")
            meta_line = " · ".join(meta_parts)

            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": title_line},
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": meta_line}],
                },
            ]
            if summary_text:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*[Summary]*\n{summary_text}"},
                })
            else:
                # Fallback to original abstract if summary is empty
                abstract = paper.abstract[:300] + "..." if len(paper.abstract) > 300 else paper.abstract
                if abstract:
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*[Abstract]*\n{abstract}"},
                    })

            fallback = f"{paper.title}\n{meta_line}\n{summary_text}"
            _post(client, config.slack_channel, fallback, thread_ts=thread_ts, blocks=blocks)

    print(f"Sent digest to #{config.slack_channel} ({total} papers in thread)")


def _post(
    client: WebClient,
    channel: str,
    text: str,
    thread_ts: str | None = None,
    blocks: list | None = None,
) -> str | None:
    try:
        result = client.chat_postMessage(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            blocks=blocks,
        )
        return result["ts"]
    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")
        return None
