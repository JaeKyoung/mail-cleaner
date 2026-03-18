from mail_cleaner.config import Config
from mail_cleaner.dedup import group_and_dedup
from mail_cleaner.gmail_client import fetch_scholar_emails, get_gmail_service
from mail_cleaner.models import DailyDigest
from mail_cleaner.scholar_parser import parse_email


def run_digest_pipeline(
    config: Config,
    max_results: int | None = None,
    days_back: int | None = None,
) -> tuple[list[DailyDigest], int, int]:
    """
    Run the full pipeline: fetch → parse → dedup.

    Args:
        config: Configuration object
        max_results: Override config.max_results if provided
        days_back: Override config.days_back if provided

    Returns:
        Tuple of (digests, num_emails, num_parsed)
    """
    actual_days = days_back if days_back is not None else config.days_back
    print(f"Fetching Scholar emails from the last {actual_days} days...")

    service = get_gmail_service(config)
    raw_emails = fetch_scholar_emails(service, config, max_results, days_back)
    print(f"Found {len(raw_emails)} emails.")

    all_papers = []
    for email in raw_emails:
        papers = parse_email(email)
        all_papers.extend(papers)

    print(f"Parsed {len(all_papers)} papers total.")

    digests = group_and_dedup(all_papers)

    return digests, len(raw_emails), len(all_papers)
