import click

from larklab.cli.common import CONTEXT_SETTINGS
from larklab.config import load_config
from larklab.database.embedder import embed_paper
from larklab.database.repository import PaperRepository
from larklab.extract.abstract_fetcher import extract_doi
from larklab.extract.paper_fetcher import fetch_paper
from larklab.schemas import Paper


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
        if doi:
            existing.doi = doi
        if title or abstract:
            existing.embedding = embed_paper(existing)

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
            limit = 20 if journal else 5
            results = repo.search_similar(embedding, limit=limit)
            if journal:
                results = [(p, d) for p, d in results if j in p.journal.lower()]
                results = results[:5]

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
