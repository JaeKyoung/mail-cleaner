import logging
import time
from dataclasses import replace
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from larklab.schemas import Paper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; larklab/0.1)",
    "Accept": "text/html",
}


def fetch_full_abstracts(papers: list[Paper], delay: float = 2.0) -> list[Paper]:
    """Fetch full abstracts from paper URLs.

    Returns new Paper list with updated abstracts.
    """
    results = []
    with httpx.Client(follow_redirects=True, timeout=15, headers=_HEADERS) as client:
        for i, paper in enumerate(papers):
            if i > 0:
                time.sleep(delay)
            url = _resolve_url(paper.url)
            if not url:
                results.append(paper)
                continue
            abstract = _fetch_abstract(client, url, delay)
            if abstract and len(abstract) > len(paper.abstract):
                results.append(replace(paper, abstract=abstract))
            else:
                results.append(paper)
    return results


def _resolve_url(url: str) -> str | None:
    """Extract real URL from Google Scholar redirect, normalize arxiv URLs."""
    if not url:
        return None
    parsed = urlparse(url)
    if "scholar.google" in parsed.hostname and parsed.path.startswith("/scholar_url"):
        qs = parse_qs(parsed.query)
        real = qs.get("url", [None])[0]
        if real:
            url = real
            parsed = urlparse(url)
    # arxiv: /pdf/ID -> /abs/ID
    if parsed.hostname and "arxiv.org" in parsed.hostname and "/pdf/" in parsed.path:
        url = url.replace("/pdf/", "/abs/", 1)
    return url


def _fetch_abstract(client: httpx.Client, url: str, delay: float) -> str | None:
    """Fetch and parse abstract from URL with retry for transient errors."""
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            resp = client.get(url)
            if 400 <= resp.status_code < 500:
                logger.debug("Client error %d for %s, skipping", resp.status_code, url)
                return None
            resp.raise_for_status()
            return _parse_abstract(resp.text, url)
        except ValueError as e:
            logger.debug(
                "Parse error for %s (likely binary response), skipping: %s", url, e
            )
            return None
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
            if attempt < max_retries:
                logger.debug("Retry %d for %s: %s", attempt + 1, url, e)
                time.sleep(delay)
            else:
                logger.debug(
                    "Failed after %d attempts for %s: %s", max_retries + 1, url, e
                )
                return None


def _parse_abstract(html: str, url: str) -> str | None:
    """Extract abstract from HTML based on site."""
    soup = BeautifulSoup(html, "html.parser")
    if "arxiv.org" in url:
        return _parse_arxiv(soup)
    if "pubmed" in url:
        return _parse_pubmed(soup)
    if "nature.com" in url:
        return _parse_nature(soup) or _parse_generic(soup)
    return _parse_generic(soup)


def _parse_arxiv(soup: BeautifulSoup) -> str | None:
    block = soup.find("blockquote", class_="abstract")
    if block:
        # Remove the "Abstract:" descriptor if present
        desc = block.find("span", class_="descriptor")
        if desc:
            desc.decompose()
        return block.get_text(strip=True)
    return None


def _parse_pubmed(soup: BeautifulSoup) -> str | None:
    div = soup.find("div", class_="abstract-content")
    if div:
        return div.get_text(strip=True)
    return None


def _parse_nature(soup: BeautifulSoup) -> str | None:
    div = soup.select_one("#Abs1-content")
    if div:
        for sup in div.find_all("sup"):
            sup.decompose()
        return div.get_text(strip=True)
    return None


def _parse_generic(soup: BeautifulSoup) -> str | None:
    for name in ("citation_abstract", "og:description", "description"):
        meta = soup.find("meta", attrs={"name": name}) or soup.find(
            "meta", attrs={"property": name}
        )
        if meta and meta.get("content"):
            return meta["content"].strip()
    return None
