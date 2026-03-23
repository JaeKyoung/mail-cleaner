import logging
import re
import time
from dataclasses import replace
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup

from larklab.schemas import Paper, ScholarPaper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; larklab/0.1)",
    "Accept": "text/html",
}


def fetch_full_abstracts[P: (Paper, ScholarPaper)](
    papers: list[P], delay: float = 2.0
) -> list[P]:
    """Fetch full abstracts from paper URLs.

    Tries PubMed E-utilities API first, falls back to HTTP crawling.
    Returns new Paper list with updated abstracts.
    """
    results = []
    with httpx.Client(follow_redirects=True, timeout=15, headers=_HEADERS) as client:
        for i, paper in enumerate(papers):
            if i > 0:
                time.sleep(delay)
            try:
                url = _resolve_url(paper.url)
                doi = extract_doi(url) if url else None
                # 1. PubMed: DOI first, then title fallback
                abstract, pubmed_doi = None, None
                if doi:
                    abstract, pubmed_doi = _fetch_abstract_pubmed(client, f"{doi}[doi]")
                if not abstract or len(abstract) <= len(paper.abstract):
                    alt_abstract, alt_doi = _fetch_abstract_pubmed(
                        client, f"{paper.title}[Title]"
                    )
                    if alt_abstract and (not abstract or len(alt_abstract) > len(abstract)):
                        abstract = alt_abstract
                        if not doi:
                            doi = alt_doi
                doi = doi or pubmed_doi
                # 2. CrossRef (DOI)
                if doi and (not abstract or len(abstract) <= len(paper.abstract)):
                    abstract = _fetch_abstract_crossref(client, doi) or abstract
                # 3. HTTP crawling fallback
                if not abstract or len(abstract) <= len(paper.abstract):
                    if url:
                        abstract = _fetch_abstract(client, url, delay)
                updates = {}
                if abstract and len(abstract) > len(paper.abstract):
                    updates["abstract"] = abstract
                if doi and not paper.doi:
                    updates["doi"] = doi
                results.append(replace(paper, **updates) if updates else paper)
            except Exception:
                logger.debug("Failed to fetch abstract for %s, skipping", paper.title)
                results.append(paper)
    return results


def _resolve_url(url: str) -> str | None:
    """Extract real URL from Google Scholar redirect, normalize to abstract pages."""
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
    if parsed.hostname and "arxiv.org" in parsed.hostname:
        if "/pdf/" in parsed.path:
            url = url.replace("/pdf/", "/abs/", 1)
        # Strip .pdf extension if present
        url = re.sub(r"\.pdf$", "", url)
    # bioRxiv/medRxiv: strip .full.pdf, .full, .abstract suffixes
    if parsed.hostname and (
        "biorxiv.org" in parsed.hostname or "medrxiv.org" in parsed.hostname
    ):
        url = re.sub(r"\.(full(\.pdf)?|abstract|pdf)$", "", url)
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
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError, httpx.HTTPStatusError) as e:
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


def _fetch_abstract_pubmed(
    client: httpx.Client, query: str
) -> tuple[str | None, str | None]:
    """Fetch abstract and DOI from PubMed.

    Query should include field tag (e.g. [Title], [doi]).
    """
    if not query:
        return None, None
    ids = pubmed_esearch(client, query)
    if not ids:
        return None, None
    soup = pubmed_efetch(client, ids[0])
    if not soup:
        return None, None
    abstract_tag = soup.find("abstracttext")
    abstract = abstract_tag.text if abstract_tag else None
    doi = None
    doi_tag = soup.find("articleid", idtype="doi")
    if doi_tag:
        doi = doi_tag.text
    return abstract, doi


def clean_crossref_abstract(raw: str) -> str:
    """Clean CrossRef abstract: strip HTML tags, 'Abstract' prefix, whitespace."""
    text = re.sub(r"<[^>]+>", "", raw)
    text = re.sub(r"^\s*Abstract\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*—[A-Z]{1,4}\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch_abstract_crossref(client: httpx.Client, doi: str) -> str | None:
    """Fetch abstract from CrossRef API."""
    try:
        resp = client.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        abstract = clean_crossref_abstract(resp.json()["message"].get("abstract", ""))
        return abstract or None
    except Exception:
        logger.debug("CrossRef failed for DOI: %s", doi)
        return None


def extract_doi(url: str) -> str | None:
    """Extract DOI from a URL. Synthesizes arXiv DOI from abs URL."""
    # arXiv abs URL → synthetic DOI
    arxiv_match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", url)
    if arxiv_match:
        return f"10.48550/arXiv.{arxiv_match.group(1)}"
    match = re.search(r"(10\.\d{4,}/[^\s?#]+)", url)
    if not match:
        return None
    doi = match.group(1).rstrip("/")
    # Remove bioRxiv/medRxiv URL suffixes (.full.pdf, .full, .abstract, etc.)
    doi = re.sub(r"\.(full(\.pdf)?|abstract|pdf)$", "", doi)
    return doi


def pubmed_esearch(client: httpx.Client, term: str) -> list[str]:
    """Search PubMed and return list of PMIDs."""
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={quote_plus(term)}&retmode=json"
    )
    try:
        resp = client.get(url)
        return resp.json()["esearchresult"]["idlist"]
    except Exception:
        logger.debug("PubMed esearch failed for term: %s", term)
        return []


def pubmed_efetch(client: httpx.Client, pmid: str) -> BeautifulSoup | None:
    """Fetch PubMed article XML and return parsed soup."""
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&rettype=abstract&retmode=xml"
    )
    try:
        resp = client.get(url)
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        logger.debug("PubMed efetch failed for PMID: %s", pmid)
        return None
