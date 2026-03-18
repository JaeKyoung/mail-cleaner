"""Test sending a small digest to Slack."""

from mail_cleaner.config import load_config
from mail_cleaner.dedup import group_and_dedup
from mail_cleaner.gmail_client import fetch_scholar_emails, get_gmail_service
from mail_cleaner.scholar_parser import parse_email
from mail_cleaner.slack_output import send_digest_to_slack


def main():
    config = load_config()
    config.max_results = 1  # small test

    service = get_gmail_service(config)
    raw_emails = fetch_scholar_emails(service, config)

    all_papers = []
    for email in raw_emails:
        papers = parse_email(email)
        all_papers.extend(papers)

    digests = group_and_dedup(all_papers)
    print(f"Sending {sum(len(d.papers) for d in digests)} papers to Slack...")
    send_digest_to_slack(
        digests, config,
        num_emails=len(raw_emails),
        num_parsed=len(all_papers),
    )


if __name__ == "__main__":
    main()
