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
    received_at: datetime
    summary: str = ""


@dataclass
class DailyDigest:
    date: date
    papers: list[Paper] = field(default_factory=list)
