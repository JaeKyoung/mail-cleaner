from datetime import UTC, datetime

from larklab.config import Config
from larklab.extract.abstract_fetcher import fetch_full_abstracts
from larklab.extract.gmail_client import GmailClient
from larklab.models import DailyDigest
from larklab.transform.dedup import group_and_dedup
from larklab.transform.summarizer import summarize_abstract

GAP_HOURS = 2


def _detect_batches(
    dated_msgs: list[tuple[str, int]],
) -> list[list[tuple[str, int]]]:
    """Group messages into batches by time gap.

    Returns batches sorted newest-first.
    """
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
        dt = datetime.fromtimestamp(newest_ts / 1000, tz=UTC).astimezone()
        parts.append(f"Batch {i + 1} ({len(batch)} emails, {dt:%m/%d %H:%M})")
    print(f"Found {len(batches)} batches: {' | '.join(parts)}")
    if num_batches is not None:
        selected = batches[:num_batches]
        total_emails = sum(len(b) for b in selected)
        print(f"Processing latest {num_batches} batch(es) ({total_emails} emails)...")


def run_digest_pipeline(
    config: Config,
    gmail: GmailClient,
    max_results: int | None = None,
    days_back: int | None = None,
    fetch_abstracts: bool = True,
    num_batches: int | None = None,
) -> tuple[list[DailyDigest], int, int]:
    """Run the full pipeline: fetch -> parse -> dedup -> fetch abstracts.

    Returns:
        Tuple of (digests, num_emails, num_parsed)
    """
    actual_days = days_back if days_back is not None else config.days_back
    actual_max = max_results if max_results is not None else config.max_results
    print(f"Fetching Scholar emails from the last {actual_days} days...")

    if num_batches is not None:
        msg_ids = gmail.list_message_ids(config.scholar_query, actual_max, actual_days)
        if not msg_ids:
            print("Found 0 emails.")
            return [], 0, 0
        print(f"Found {len(msg_ids)} emails, detecting batches...")
        dated_msgs = gmail.fetch_internal_dates(msg_ids)
        batches = _detect_batches(dated_msgs)
        _print_batch_info(batches, num_batches)
        selected = batches[:num_batches]
        selected_ids = [mid for batch in selected for mid, _ in batch]
        raw_emails = gmail.fetch_full_messages(selected_ids)
        num_emails = len(raw_emails)
        print(f"Found {num_emails} emails.")
        all_papers = gmail.parse_emails(raw_emails)
    else:
        all_papers, num_emails = gmail.fetch_and_parse(
            config.scholar_query, actual_max, actual_days
        )
        print(f"Found {num_emails} emails.")

    print(f"Parsed {len(all_papers)} papers total.")

    digests = group_and_dedup(all_papers)

    if fetch_abstracts:
        for digest in digests:
            print(
                f"Fetching full abstracts for {len(digest.papers)} papers "
                f"({digest.date})..."
            )
            digest.papers = fetch_full_abstracts(digest.papers)

    if config.use_summary:
        for digest in digests:
            for i, paper in enumerate(digest.papers):
                print(f"  Summarizing paper {i + 1}/{len(digest.papers)}...")
                paper.summary = summarize_abstract(paper, model=config.ollama_model)

    return digests, num_emails, len(all_papers)
