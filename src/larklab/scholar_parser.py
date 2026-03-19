import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from larklab.models import Paper


def _get_html_body(payload: dict) -> str | None:
    """Extract HTML body from Gmail message payload (handles MIME parts)."""
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _get_html_body(part)
        if result:
            return result

    return None


def _get_received_at(headers: list[dict]) -> datetime:
    """Extract the date from email headers."""
    for header in headers:
        if header["name"].lower() == "date":
            # Gmail date format: "Mon, 18 Mar 2026 10:00:00 +0000"
            try:
                return parsedate_to_datetime(header["value"])
            except (ValueError, TypeError):
                pass
    return datetime.now(timezone.utc)


def parse_email(raw_message: dict) -> list[Paper]:
    """Parse a Google Scholar alert email into a list of Paper objects."""
    payload = raw_message.get("payload", {})
    headers = payload.get("headers", [])
    message_id = raw_message.get("id", "")
    received_at = _get_received_at(headers)

    html = _get_html_body(payload)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    papers = []

    # Google Scholar alerts use <h3> tags with class "gse_alrt_title" for paper titles.
    # Each paper block contains the title link, authors, and a snippet.
    title_tags = soup.find_all("h3")

    for tag in title_tags:
        link = tag.find("a")
        if not link:
            continue

        title = link.get_text(strip=True)
        url = link.get("href", "")

        # Authors and abstract are in sibling elements after the <h3>
        authors_text = ""
        abstract_text = ""

        next_div = tag.find_next_sibling("div")
        if next_div:
            # First div after title typically contains authors
            author_span = next_div.find("span", style=lambda s: s and "color" in s) if next_div else None
            if author_span:
                authors_text = author_span.get_text(strip=True)
            else:
                authors_text = next_div.get_text(strip=True)

            # Next div contains the abstract/snippet
            snippet_div = next_div.find_next_sibling("div")
            if snippet_div:
                abstract_text = snippet_div.get_text(strip=True)

        # Split authors from journal info: "A, B\xa0- Journal Name, Year"
        journal = ""
        if "\xa0- " in authors_text:
            authors_part, journal = authors_text.split("\xa0- ", 1)
        elif " - " in authors_text:
            authors_part, journal = authors_text.split(" - ", 1)
        else:
            authors_part = authors_text

        authors = [a.strip() for a in authors_part.split(",") if a.strip()] if authors_part else []

        papers.append(
            Paper(
                title=title,
                authors=authors,
                journal=journal.strip(),
                abstract=abstract_text,
                url=url,
                source_email_id=message_id,
                received_at=received_at,
            )
        )

    return papers
