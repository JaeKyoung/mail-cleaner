from larklab.models import DailyDigest


def print_digest(digests: list[DailyDigest]) -> None:
    """Print the digest to console in a readable format."""
    if not digests:
        print("No papers found.")
        return

    total = sum(len(d.papers) for d in digests)
    print(f"\n{'=' * 60}")
    print(f"  Google Scholar Digest — {total} papers, {len(digests)} days")
    print(f"{'=' * 60}\n")

    for digest in digests:
        print(f"--- {digest.date} ({len(digest.papers)} papers) ---\n")

        for i, paper in enumerate(digest.papers, 1):
            authors = ", ".join(paper.authors) if paper.authors else "Unknown"

            print(f"  {i}. {paper.title}")
            print(f"     Authors: {authors}")
            if paper.journal:
                print(f"     Journal: {paper.journal}")
            if paper.abstract:
                print(f"     Abstract: {paper.abstract}")
            print(f"     URL: {paper.url}")
            print()
