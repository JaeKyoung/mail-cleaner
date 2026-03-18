from mail_cleaner.config import load_config
from mail_cleaner.dedup import group_and_dedup
from mail_cleaner.gmail_client import fetch_scholar_emails, get_gmail_service
from mail_cleaner.output import print_digest
from mail_cleaner.scholar_parser import parse_email
from mail_cleaner.slack_output import send_digest_to_slack


def main():
    config = load_config()
    print(f"Fetching Scholar emails from the last {config.days_back} days...")

    service = get_gmail_service(config)
    raw_emails = fetch_scholar_emails(service, config)
    print(f"Found {len(raw_emails)} emails.")

    all_papers = []
    for email in raw_emails:
        papers = parse_email(email)
        all_papers.extend(papers)

    print(f"Parsed {len(all_papers)} papers total.")

    digests = group_and_dedup(all_papers)
    print_digest(digests)
    send_digest_to_slack(
        digests, config,
        num_emails=len(raw_emails),
        num_parsed=len(all_papers),
    )


if __name__ == "__main__":
    main()
