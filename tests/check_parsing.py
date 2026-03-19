"""Fetch a few Scholar emails and inspect parsing results in detail."""

from larklab.config import load_config
from larklab.extract.gmail_client import GmailClient
from larklab.extract.scholar_parser import _get_html_body, parse_email


def main():
    config = load_config()
    config.scholar_query = "from:scholaralerts-noreply@google.com"
    config.max_results = 3  # just a few emails for inspection
    config.days_back = 7

    gmail = GmailClient(config)
    raw_emails = gmail.fetch_emails(
        config.scholar_query, config.max_results, config.days_back
    )

    for i, email in enumerate(raw_emails):
        print(f"\n{'=' * 70}")
        print(f"EMAIL {i + 1} (id: {email['id']})")
        print(f"{'=' * 70}")

        # Show subject
        headers = email.get("payload", {}).get("headers", [])
        subject = next(
            (h["value"] for h in headers if h["name"].lower() == "subject"),
            "N/A",
        )
        print(f"Subject: {subject}\n")

        # Show raw HTML (first 500 chars)
        html = _get_html_body(email.get("payload", {}))
        if html:
            print("--- Raw HTML (first 500 chars) ---")
            print(html[:500])
            print("...\n")

        # Show parsed results
        papers = parse_email(email)
        print(f"--- Parsed {len(papers)} papers ---\n")

        for j, paper in enumerate(papers, 1):
            print(f"  [{j}]")
            print(f"  Title:    {paper.title}")
            print(f"  Authors:  {paper.authors}")
            print(f"  Journal:  {paper.journal}")
            abstract_preview = paper.abstract[:150]
            ellipsis = "..." if len(paper.abstract) > 150 else ""
            print(f"  Abstract: {abstract_preview}{ellipsis}")
            print(f"  URL:      {paper.url}")
            print(f"  Date:     {paper.received_at}")
            print()


if __name__ == "__main__":
    main()
