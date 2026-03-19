"""Fetch a few Scholar emails and inspect parsing results in detail."""

from larklab.config import load_config
from larklab.gmail_client import fetch_scholar_emails, get_gmail_service
from larklab.scholar_parser import parse_email, _get_html_body


def main():
    config = load_config()
    config.max_results = 3  # just a few emails for inspection

    service = get_gmail_service(config)
    raw_emails = fetch_scholar_emails(service, config)

    for i, email in enumerate(raw_emails):
        print(f"\n{'=' * 70}")
        print(f"EMAIL {i + 1} (id: {email['id']})")
        print(f"{'=' * 70}")

        # Show subject
        headers = email.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "N/A")
        print(f"Subject: {subject}\n")

        # Show raw HTML (first 500 chars)
        html = _get_html_body(email.get("payload", {}))
        if html:
            print(f"--- Raw HTML (first 500 chars) ---")
            print(html[:500])
            print(f"...\n")

        # Show parsed results
        papers = parse_email(email)
        print(f"--- Parsed {len(papers)} papers ---\n")

        for j, paper in enumerate(papers, 1):
            print(f"  [{j}]")
            print(f"  Title:    {paper.title}")
            print(f"  Authors:  {paper.authors}")
            print(f"  Journal:  {paper.journal}")
            print(f"  Abstract: {paper.abstract[:150]}{'...' if len(paper.abstract) > 150 else ''}")
            print(f"  URL:      {paper.url}")
            print(f"  Date:     {paper.received_at}")
            print()


if __name__ == "__main__":
    main()
