"""Test sending a small digest to Slack."""

from larklab.config import load_config
from larklab.extract.gmail_client import GmailClient
from larklab.extract.scholar_parser import parse_email
from larklab.load.slack import send_digest_to_slack
from larklab.transform.dedup import group_and_dedup


def main():
    config = load_config()
    config.scholar_query = "from:scholaralerts-noreply@google.com"
    config.max_results = 1  # small test
    config.days_back = 7
    config.slack_channel = "journal-club"

    gmail = GmailClient(config)
    raw_emails = gmail.fetch_emails(
        config.scholar_query, config.max_results, config.days_back
    )

    all_papers = []
    for email in raw_emails:
        papers = parse_email(email)
        all_papers.extend(papers)

    digests = group_and_dedup(all_papers)
    print(f"Sending {sum(len(d.papers) for d in digests)} papers to Slack...")
    send_digest_to_slack(
        digests,
        config,
        num_emails=len(raw_emails),
        num_parsed=len(all_papers),
    )


if __name__ == "__main__":
    main()
