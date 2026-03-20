from datetime import UTC, datetime

from larklab.config import Config
from larklab.database.embedder import embed_paper
from larklab.database.repository import PaperRepository
from larklab.extract.abstract_fetcher import fetch_full_abstracts
from larklab.extract.gmail_client import GmailClient
from larklab.schemas import DailyDigest
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

    # Always detect batches
    msg_ids = gmail.list_message_ids(config.scholar_query, actual_max, actual_days)
    if not msg_ids:
        print("Found 0 emails.")
        return [], 0, 0

    print(f"Found {len(msg_ids)} emails, detecting batches...")
    dated_msgs = gmail.fetch_internal_dates(msg_ids)
    batches = _detect_batches(dated_msgs)
    _print_batch_info(batches, num_batches)

    if num_batches is not None:
        batches = batches[:num_batches]

    selected_ids = [mid for batch in batches for mid, _ in batch]
    raw_emails = gmail.fetch_full_messages(selected_ids)
    num_emails = len(raw_emails)
    print(f"Processing {num_emails} emails.")
    all_papers = gmail.parse_emails(raw_emails)

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

    # Compute similarity scores against reference papers
    with PaperRepository(config.db_path) as repo:
        refs = repo.get_papers()
        if refs:
            _score_similarity(digests, repo)
        else:
            print("No reference papers in DB — skipping similarity scoring.")

    # Sort papers so same top-1 reference papers are adjacent
    for digest in digests:
        digest.papers.sort(
            key=lambda p: p.similar_papers[0][0] if p.similar_papers else ""
        )

    return digests, num_emails, len(all_papers)


def _score_similarity(
    digests: list[DailyDigest],
    repo: PaperRepository,
) -> None:
    """Embed papers and attach similarity score + closest reference title."""
    all_papers = [p for d in digests for p in d.papers]
    print(f"Embedding {len(all_papers)} papers for similarity scoring...")

    for i, paper in enumerate(all_papers):
        print(f"  Embedding paper {i + 1}/{len(all_papers)}...")
        paper.embedding = embed_paper(paper)
        results = repo.search_similar(paper.embedding, limit=3)
        if results:
            paper.similar_papers = [(ref.title, 1 - dist) for ref, dist in results]
