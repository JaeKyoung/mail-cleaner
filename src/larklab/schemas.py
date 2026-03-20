from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class ScholarPaper:
    """Paper from Scholar email — transient, for digest pipeline."""

    title: str
    authors: list[str]
    journal: str
    abstract: str
    url: str
    source_email_id: str
    received_at: datetime | None
    summary: str = ""
    doi: str | None = None
    embedding: list[float] | None = None
    similar_papers: list[tuple[str, float]] | None = None  # [(title, score)]

    def to_paper(self) -> "Paper":
        """Convert to Paper for DB storage. Requires DOI."""
        if not self.doi:
            raise ValueError(f"Cannot convert to Paper without DOI: {self.title}")
        return Paper(
            title=self.title,
            authors=self.authors,
            journal=self.journal,
            abstract=self.abstract,
            doi=self.doi,
            embedding=self.embedding,
        )


@dataclass
class Paper:
    """Reference paper stored in DB — DOI required."""

    title: str
    authors: list[str]
    journal: str
    abstract: str
    doi: str
    id: int | None = None
    embedding: list[float] | None = None

    @property
    def url(self) -> str:
        return f"https://doi.org/{self.doi}"


@dataclass
class DailyDigest:
    date: date
    papers: list[ScholarPaper] = field(default_factory=list)
