from collections import defaultdict
from datetime import datetime

from larklab.schemas import DailyDigest, ScholarPaper

_LOCAL_TZ = datetime.now().astimezone().tzinfo


def _normalize_title(title: str) -> str:
    return title.lower().strip()


def group_and_dedup(papers: list[ScholarPaper]) -> list[DailyDigest]:
    """Group papers by date and remove duplicates within each group."""
    seen_titles: set[str] = set()
    unique_papers: list[ScholarPaper] = []

    for paper in papers:
        normalized = _normalize_title(paper.title)
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique_papers.append(paper)

    by_date: dict[str, list[ScholarPaper]] = defaultdict(list)
    for paper in unique_papers:
        local_date = paper.received_at.astimezone(_LOCAL_TZ).date()
        by_date[local_date].append(paper)

    digests = [
        DailyDigest(date=d, papers=ps)
        for d, ps in sorted(by_date.items(), reverse=True)
    ]
    return digests
