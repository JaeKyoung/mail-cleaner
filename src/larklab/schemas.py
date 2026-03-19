from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Paper:
    title: str
    authors: list[str]
    journal: str
    abstract: str
    url: str
    source_email_id: str
    received_at: datetime | None
    summary: str = ""
    id: int | None = None
    embedding: list[float] | None = None
    similar_papers: list[tuple[str, float]] | None = None  # [(title, score)]


@dataclass
class DailyDigest:
    date: date
    papers: list[Paper] = field(default_factory=list)
