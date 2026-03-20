import re
import warnings

import arxiv
import click
import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from larklab.cli.common import CONTEXT_SETTINGS
from larklab.config import load_config
from larklab.database.embedder import embed_paper
from larklab.database.repository import PaperRepository
from larklab.extract.abstract_fetcher import (
    clean_crossref_abstract,
    extract_doi,
    pubmed_efetch,
    pubmed_esearch,
)
from larklab.schemas import Paper

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def _make_paper(
    title: str = "",
    authors: list[str] | None = None,
    journal: str = "",
    abstract: str = "",
    doi: str = "",
) -> Paper:
    """Create a Paper for DB storage."""
    return Paper(
        title=title,
        authors=authors or [],
        journal=journal,
        abstract=abstract,
        doi=doi,
    )


def _format_authors(authors: list[str]) -> str:
    """Format authors list for display (max 3 + et al.)."""
    s = ", ".join(authors[:3])
    if len(authors) > 3:
        s += " et al."
    return s or "(none)"


# --- Fetch functions ---


def fetch_paper(doi: str, url: str = "") -> Paper:
    """Fetch paper metadata by DOI. Falls back to URL if DOI unavailable.

    Priority: PubMed → arXiv → bioRxiv → CrossRef → HTML.
    """
    # 1. PubMed (DOI)
    if doi:
        result = _fetch_from_pubmed(doi)
        if result and result.title:
            result.doi = doi
            return result

    # 2. arXiv API
    if doi and doi.startswith("10.48550/arXiv"):
        return _fetch_from_arxiv_api(doi)
    if url and "arxiv.org" in url:
        return _fetch_from_arxiv_api(url)

    # 3. bioRxiv/medRxiv API
    if doi and doi.startswith("10.1101/"):
        return _fetch_from_biorxiv_api(doi)
    if url and ("biorxiv.org" in url or "medrxiv.org" in url):
        return _fetch_from_biorxiv_api(url)

    # 4. CrossRef (DOI)
    if doi:
        result = _fetch_from_crossref(doi)
        if result and result.title:
            return result

    # 5. HTML crawling (last resort)
    if url:
        return _fetch_from_html(url, doi)

    return _make_paper(doi=doi or "")


def _fetch_from_crossref(doi: str) -> Paper:
    """Fetch paper metadata from CrossRef API."""
    api_url = f"https://api.crossref.org/works/{doi}"
    resp = httpx.get(api_url, timeout=15)
    if resp.status_code != 200:
        print(f"CrossRef API returned {resp.status_code}")
        return _make_paper(doi=doi or "")

    data = resp.json()["message"]
    title = (data.get("title") or [""])[0]
    authors = [
        f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
        for a in data.get("author", [])
    ]
    journal = (data.get("container-title") or [""])[0]

    abstract = clean_crossref_abstract(data.get("abstract", ""))

    return _make_paper(
        title=title,
        authors=authors,
        journal=journal,
        abstract=abstract,
        doi=doi,
    )


def _fetch_from_html(url: str, doi: str | None) -> Paper:
    """Fetch paper metadata by crawling the URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; larklab/0.1)",
        "Accept": "text/html",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=15, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError) as e:
        print(f"HTML fetch failed: {e}")
        return _make_paper(doi=doi or "")

    soup = BeautifulSoup(resp.text, "html.parser")

    if soup.select_one("#challenge-error-text"):
        print("Blocked by Cloudflare.")
        return _make_paper(doi=doi or "")

    title = ""
    meta_title = soup.find("meta", attrs={"name": "citation_title"}) or soup.find(
        "meta", attrs={"property": "og:title"}
    )
    if meta_title and meta_title.get("content"):
        title = meta_title["content"].strip()
    elif soup.title:
        title = soup.title.get_text(strip=True)

    authors = [
        tag["content"].strip()
        for tag in soup.find_all("meta", attrs={"name": "citation_author"})
        if tag.get("content")
    ]

    journal_tag = soup.find("meta", attrs={"name": "citation_journal_title"})
    journal = ""
    if journal_tag and journal_tag.get("content"):
        journal = journal_tag["content"].strip()

    if not doi:
        doi_tag = soup.find("meta", attrs={"name": "citation_doi"})
        if doi_tag and doi_tag.get("content"):
            doi = doi_tag["content"].strip()

    # Parse abstract from the already-fetched HTML
    abstract = ""
    for name in ("citation_abstract", "og:description", "description"):
        meta = soup.find("meta", attrs={"name": name}) or soup.find(
            "meta", attrs={"property": name}
        )
        if meta and meta.get("content"):
            abstract = meta["content"].strip()
            break

    return _make_paper(
        title=title, authors=authors, journal=journal, abstract=abstract, doi=doi or ""
    )


def _fetch_from_pubmed(doi: str) -> Paper | None:
    """Fetch paper metadata from PubMed via DOI."""
    with httpx.Client(timeout=15) as client:
        ids = pubmed_esearch(client, f"{doi}[doi]")
        if not ids:
            return None
        soup = pubmed_efetch(client, ids[0])
    if not soup:
        return None

    title_tag = soup.find("articletitle")
    title = title_tag.text if title_tag else ""

    authors = []
    for a in soup.find_all("author"):
        last = a.find("lastname")
        first = a.find("forename")
        if last:
            name = last.text
            if first:
                name += f", {first.text}"
            authors.append(name)

    # Journal title is inside <journal><title>
    journal = ""
    journal_el = soup.find("journal")
    if journal_el:
        jtitle = journal_el.find("title")
        if jtitle:
            journal = jtitle.text

    abstract_tag = soup.find("abstracttext")
    abstract = abstract_tag.text if abstract_tag else ""

    return _make_paper(
        title=title,
        authors=authors,
        journal=journal,
        abstract=abstract,
        doi=doi,
    )


def _fetch_from_arxiv_api(url: str) -> Paper:
    """Fetch paper metadata from arXiv API."""
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", url)
    if not match:
        print(f"Could not extract arXiv ID from {url}")
        return _make_paper()

    arxiv_id = match.group(1)
    client = arxiv.Client()
    search = arxiv.Search(id_list=[arxiv_id])
    results = list(client.results(search))

    if not results:
        print(f"No results from arXiv API for {arxiv_id}")
        return _make_paper()

    r = results[0]
    return _make_paper(
        title=r.title,
        authors=[a.name for a in r.authors],
        journal="arXiv",
        abstract=r.summary.replace("\n", " "),
        doi=r.doi or f"10.48550/arXiv.{arxiv_id}",
    )


def _fetch_from_biorxiv_api(url: str) -> Paper:
    """Fetch paper metadata from bioRxiv/medRxiv API."""
    match = re.search(r"(10\.\d{4,}/[\d.]+)", url)
    if not match:
        print(f"Could not extract DOI from {url}")
        return _make_paper()

    doi = match.group(1)
    api_url = f"https://api.biorxiv.org/details/biorxiv/{doi}"

    resp = httpx.get(api_url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("collection"):
        print(f"No results from bioRxiv API for {doi}")
        return _make_paper()

    p = data["collection"][-1]
    abstract = p.get("abstract", "")
    abstract = re.sub(r"[A-Z]+_SCPLOW[A-Z]*C_SCPLOW", "", abstract)
    abstract = re.sub(r"\d+$", "", abstract)
    abstract = abstract.strip()

    return _make_paper(
        title=p.get("title", "").strip(),
        authors=[a.strip() for a in p.get("authors", "").split(";")],
        journal=p.get("server", "biorxiv").capitalize(),
        abstract=abstract,
        doi=doi,
    )


# --- CLI commands ---


@click.command("db-add", context_settings=CONTEXT_SETTINGS)
@click.argument("url_or_doi")
@click.option("--title", default=None, help="Override paper title")
@click.option(
    "--authors",
    default=None,
    help="Override authors (pipe-separated, e.g. 'A|B')",
)
@click.option("--journal", default=None, help="Override journal name")
@click.option("--abstract", default=None, help="Override paper abstract")
def add_paper(url_or_doi, title, authors, journal, abstract):
    """Add a paper by URL or DOI"""
    config = load_config()

    # Extract DOI from input
    if url_or_doi.startswith("10."):
        doi = url_or_doi
        url = ""
    else:
        doi = extract_doi(url_or_doi) or ""
        url = url_or_doi

    print(f"Fetching paper (DOI: {doi or 'unknown'})...")
    paper = fetch_paper(doi, url)

    if title:
        paper.title = title
    if authors:
        paper.authors = [a.strip() for a in authors.split("|")]
    if journal:
        paper.journal = journal
    if abstract:
        paper.abstract = abstract

    if not paper.title:
        print("Error: Could not extract paper title.")
        print("Use --title to provide it manually.")
        return

    print(f"\n  Title:    {paper.title}")
    print(f"  Authors:  {_format_authors(paper.authors)}")
    print(f"  Journal:  {paper.journal or '(none)'}")
    print(f"  Abstract: {paper.abstract or '(none)'}")

    missing = []
    if not paper.authors:
        missing.append("authors")
    if not paper.journal:
        missing.append("journal")
    if not paper.abstract:
        missing.append("abstract")
    if missing:
        print(f"\n  Missing: {', '.join(missing)}")

    print()
    if not click.confirm("Proceed?", default=len(missing) == 0):
        print("Cancelled.")
        return

    print("Generating embedding...")
    paper.embedding = embed_paper(paper)

    with PaperRepository(config.db_path) as repo:
        matches = repo.find_similar_existing(paper)
        for i, (existing, score) in enumerate(matches):
            print(f"\nSimilar paper ({i + 1}/{len(matches)}, similarity: {score:.3f}):")
            print(f"  [{existing.id}] {existing.title}")
            print(f"  {_format_authors(existing.authors)} — {existing.journal}")
            print(f"  {existing.url}")
            print()
            choice = click.prompt(
                "Action",
                type=click.Choice(["update", "new", "skip"]),
                default="new",
                prompt_suffix=(
                    "\n  update = this is the same paper, overwrite"
                    "\n  new    = different paper, check next"
                    "\n  skip   = cancel\n> "
                ),
            )
            if choice == "update":
                repo.update(existing.id, paper)
                print(f"Updated paper (id={existing.id}).")
                return
            elif choice == "skip":
                print("Skipped.")
                return

        paper_id = repo.save(paper)
        print(f"Saved (id={paper_id}).")


@click.command("db-edit", context_settings=CONTEXT_SETTINGS)
@click.argument("paper_id", type=int)
@click.option("--title", default=None, help="New title")
@click.option(
    "--authors",
    default=None,
    help="New authors (pipe-separated, e.g. 'A|B')",
)
@click.option("--journal", default=None, help="New journal name")
@click.option("--abstract", default=None, help="New abstract")
@click.option("--doi", default=None, help="New DOI")
def edit_paper(paper_id, title, authors, journal, abstract, doi):
    """Edit fields of an existing paper"""
    config = load_config()
    with PaperRepository(config.db_path) as repo:
        existing = repo.get_by_id(paper_id)
        if existing is None:
            print(f"Paper {paper_id} not found.")
            return

        if title:
            existing.title = title
        if authors:
            existing.authors = [a.strip() for a in authors.split("|")]
        if journal:
            existing.journal = journal
        if abstract:
            existing.abstract = abstract
            existing.embedding = embed_paper(existing)
        if doi:
            existing.doi = doi

        repo.update(paper_id, existing)
        print(f"Updated paper (id={paper_id}).")


@click.command("db-search", context_settings=CONTEXT_SETTINGS)
@click.argument("query", required=False, default=None)
@click.option("--journal", default=None, help="Filter by journal name")
def search_paper(query, journal):
    """Search papers in DB by keyword, journal, or similarity"""
    if not query and not journal:
        print("Provide a query or --journal to search.")
        return

    config = load_config()
    with PaperRepository(config.db_path) as repo:
        papers = repo.get_papers()
        if journal:
            j = journal.lower()
            papers = [p for p in papers if j in p.journal.lower()]

        if query:
            keyword_matches = [p for p in papers if query.lower() in p.title.lower()]
        else:
            keyword_matches = papers

        if keyword_matches:
            print(f"=== keyword matches ({len(keyword_matches)}) ===\n")
            for p in keyword_matches:
                print(f"[{p.id}] {p.title}")
                print(f"    {_format_authors(p.authors)} — {p.journal}")
                print(f"    {p.url}")
                print(f"    {p.abstract}")
                print()

        results = []
        if query:
            embedding = embed_paper(_make_paper(title=query, abstract=query))
            results = repo.search_similar(embedding, limit=5)

    if results:
        print(f"=== similar papers (top {len(results)}) ===\n")
        for p, distance in results:
            score = 1 - distance
            print(f"[{p.id}] similarity: {score:.3f}")
            print(f"    {p.title}")
            print(f"    {_format_authors(p.authors)} — {p.journal}")
            print(f"    {p.url}")
            print()

    if not keyword_matches and not results:
        print("No matches found.")


@click.command("db-delete", context_settings=CONTEXT_SETTINGS)
@click.argument("paper_id", type=int)
def delete_paper(paper_id):
    """Delete a paper from the database"""
    config = load_config()
    with PaperRepository(config.db_path) as repo:
        existing = repo.get_by_id(paper_id)
        if existing is None:
            print(f"Paper {paper_id} not found.")
            return

        print(f"  [{existing.id}] {existing.title}")
        if not click.confirm("Delete this paper?", default=False):
            print("Cancelled.")
            return

        repo.delete(paper_id)
        print(f"Deleted paper (id={paper_id}).")


@click.command("db-check", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--refetch",
    is_flag=True,
    help="Re-fetch from URL/DOI and compare with DB",
)
def check_papers(refetch):
    """Check all papers for missing or outdated fields"""
    config = load_config()
    with PaperRepository(config.db_path) as repo:
        papers = repo.get_papers()

    issues = 0
    for p in papers:
        problems = []
        if not p.title:
            problems.append("missing: title")
        if not p.authors:
            problems.append("missing: authors")
        if not p.journal:
            problems.append("missing: journal")
        if not p.abstract:
            problems.append("missing: abstract")

        if refetch:
            fetched = fetch_paper(p.doi)
            if fetched.title and fetched.title != p.title:
                problems.append(("title", p.title, fetched.title))
            if fetched.authors and fetched.authors != p.authors:
                old_a = ", ".join(p.authors) if p.authors else "(none)"
                new_a = ", ".join(fetched.authors)
                problems.append(("authors", old_a, new_a))
            if fetched.journal and fetched.journal != (p.journal or ""):
                problems.append(("journal", p.journal or "(none)", fetched.journal))
            if fetched.abstract and fetched.abstract != p.abstract:
                old_abs = (
                    (p.abstract[:80] + "...") if len(p.abstract) > 80 else p.abstract
                )
                new_abs = (
                    (fetched.abstract[:80] + "...")
                    if len(fetched.abstract) > 80
                    else fetched.abstract
                )
                problems.append(("abstract", old_abs, new_abs))

        if problems:
            issues += 1
            print(f"[{p.id}] {p.title or '(no title)'}")
            for prob in problems:
                if isinstance(prob, tuple):
                    field, old, new = prob
                    print(f"    changed: {field}")
                    print(f"      DB:      {old}")
                    print(f"      Fetched: {new}")
                else:
                    print(f"    {prob}")
            print()

    if issues == 0:
        print(f"All {len(papers)} papers OK.")
    else:
        print(f"{issues} issue(s) found.")


@click.command("db-list", context_settings=CONTEXT_SETTINGS)
def list_papers():
    """List papers in the database"""
    config = load_config()
    with PaperRepository(config.db_path) as repo:
        papers = repo.get_papers()

    if not papers:
        print("No papers found.")
        return

    print(f"=== papers ({len(papers)}) ===\n")
    for p in papers:
        print(f"[{p.id}] {p.title}")
        print(f"    {_format_authors(p.authors)} — {p.journal}")
        print(f"    {p.url}")
        print()
