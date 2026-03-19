from datetime import datetime, timezone

from larklab.abstract_fetcher import fetch_full_abstracts
from larklab.config import Config
from larklab.dedup import group_and_dedup
from larklab.gmail_client import fetch_scholar_emails, get_gmail_service
from larklab.models import DailyDigest
from larklab.scholar_parser import parse_email

GAP_HOURS = 2


def _list_message_ids(service, config: Config, max_results: int, days_back: int) -> list[str]:
    """List message IDs matching the scholar query."""
    query = f"{config.scholar_query} newer_than:{days_back}d"
    results = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return [m["id"] for m in results.get("messages", [])]


def _fetch_internal_dates(service, msg_ids: list[str]) -> list[tuple[str, int]]:
    """Fetch internalDate for each message ID via minimal get. Returns (id, timestamp_ms) pairs."""
    pairs = []
    for mid in msg_ids:
        msg = service.users().messages().get(userId="me", id=mid, format="minimal").execute()
        pairs.append((mid, int(msg["internalDate"])))
    return pairs


def _detect_batches(dated_msgs: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    """Group messages into batches by time gap. Returns batches sorted newest-first."""
    if not dated_msgs:
        return []
    sorted_msgs = sorted(dated_msgs, key=lambda x: x[1])
    gap_ms = GAP_HOURS * 3600 * 1000
    batches: list[list[tuple[str, int]]] = [[sorted_msgs[0]]]
    for msg in sorted_msgs[1:]:
        if msg[1] - batches[-1][-1][1] > gap_ms:
            batches.append([msg])
        else:
            batches[-1].append(msg)
    batches.reverse()  # newest first
    return batches


def _print_batch_info(batches: list[list[tuple[str, int]]], num_batches: int | None):
    """Print batch summary."""
    parts = []
    for i, batch in enumerate(batches):
        newest_ts = max(ts for _, ts in batch)
        dt = datetime.fromtimestamp(newest_ts / 1000, tz=timezone.utc).astimezone()
        parts.append(f"Batch {i + 1} ({len(batch)} emails, {dt:%m/%d %H:%M})")
    print(f"Found {len(batches)} batches: {' | '.join(parts)}")
    if num_batches is not None:
        selected = batches[:num_batches]
        total_emails = sum(len(b) for b in selected)
        print(f"Processing latest {num_batches} batch(es) ({total_emails} emails)...")


def _fetch_full_messages(service, msg_ids: list[str]) -> list[dict]:
    """Fetch full message content for given IDs."""
    return [
        service.users().messages().get(userId="me", id=mid, format="full").execute()
        for mid in msg_ids
    ]


def run_digest_pipeline(
    config: Config,
    max_results: int | None = None,
    days_back: int | None = None,
    fetch_abstracts: bool = True,
    num_batches: int | None = None,
) -> tuple[list[DailyDigest], int, int, object]:
    """
    Run the full pipeline: fetch → parse → dedup → fetch abstracts.

    Args:
        config: Configuration object
        max_results: Override config.max_results if provided
        days_back: Override config.days_back if provided
        fetch_abstracts: Whether to fetch full abstracts from paper URLs
        num_batches: Process only the latest N batches (None = all)

    Returns:
        Tuple of (digests, num_emails, num_parsed, gmail_service)
    """
    actual_days = days_back if days_back is not None else config.days_back
    actual_max = max_results if max_results is not None else config.max_results
    print(f"Fetching Scholar emails from the last {actual_days} days...")

    service = get_gmail_service(config)

    if num_batches is not None:
        msg_ids = _list_message_ids(service, config, actual_max, actual_days)
        if not msg_ids:
            print("Found 0 emails.")
            return [], 0, 0, service
        print(f"Found {len(msg_ids)} emails, detecting batches...")
        dated_msgs = _fetch_internal_dates(service, msg_ids)
        batches = _detect_batches(dated_msgs)
        _print_batch_info(batches, num_batches)
        selected = batches[:num_batches]
        selected_ids = [mid for batch in selected for mid, _ in batch]
        raw_emails = _fetch_full_messages(service, selected_ids)
    else:
        raw_emails = fetch_scholar_emails(service, config, max_results, days_back)

    print(f"Found {len(raw_emails)} emails.")

    all_papers = []
    for email in raw_emails:
        papers = parse_email(email)
        all_papers.extend(papers)

    print(f"Parsed {len(all_papers)} papers total.")

    digests = group_and_dedup(all_papers)

    if fetch_abstracts:
        for digest in digests:
            print(f"Fetching full abstracts for {len(digest.papers)} papers ({digest.date})...")
            digest.papers = fetch_full_abstracts(digest.papers)

    return digests, len(raw_emails), len(all_papers), service
