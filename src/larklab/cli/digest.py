import click

from larklab.cli.common import CONTEXT_SETTINGS
from larklab.config import load_config
from larklab.extract.gmail_client import GmailClient
from larklab.load.slack import send_digest_to_slack
from larklab.load.terminal import print_digest
from larklab.pipeline import run_digest_pipeline


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--max-results",
    default=200,
    help="Maximum number of emails to fetch",
    show_default=True,
)
@click.option(
    "--days-back",
    default=7,
    help="How many days back to search",
    show_default=True,
)
@click.option(
    "--model",
    default="qwen3:8b",
    help="Ollama model for summarization",
    show_default=True,
)
@click.option(
    "--summary",
    is_flag=True,
    help="Summarize abstracts with AI (Ollama)",
)
@click.option(
    "--channel",
    default="journal-club",
    help="Slack channel to post digest",
    show_default=True,
)
@click.option(
    "--query",
    default="from:scholaralerts-noreply@google.com",
    help="Gmail search query",
    show_default=True,
)
@click.option(
    "--no-fetch-abstracts",
    is_flag=True,
    help="Skip fetching full abstracts from paper URLs",
)
@click.option(
    "--no-cleanup",
    is_flag=True,
    help="Skip trashing processed emails after output",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show details of trashed emails",
)
@click.option(
    "--batches",
    default=None,
    type=int,
    help="Process only the latest N batches (default: all)",
)
@click.option(
    "--no-slack",
    is_flag=True,
    help="Skip sending digest to Slack (print only)",
)
@click.option(
    "--output-json",
    default=None,
    type=click.Path(),
    help="Also write digest results as JSON to this path",
)
def digest(
    max_results,
    days_back,
    model,
    summary,
    channel,
    query,
    no_fetch_abstracts,
    no_cleanup,
    verbose,
    batches,
    no_slack,
    output_json,
):
    """Fetch Scholar emails, summarize, and send digest to Slack"""
    config = load_config()
    config.scholar_query = query
    config.max_results = max_results
    config.days_back = days_back
    config.slack_channel = channel
    config.ollama_model = model
    config.use_summary = summary

    gmail = GmailClient(config)

    digests, num_emails, num_parsed = run_digest_pipeline(
        config,
        gmail,
        fetch_abstracts=not no_fetch_abstracts,
        num_batches=batches,
    )

    if not digests:
        print("No papers found. Nothing to send.")
        return

    if output_json:
        import json
        from dataclasses import fields
        from datetime import datetime
        from pathlib import Path

        _EXCLUDE = {"embedding", "source_email_id"}

        def _paper_dict(p):
            d = {}
            for f in fields(p):
                if f.name in _EXCLUDE:
                    continue
                v = getattr(p, f.name)
                if isinstance(v, datetime):
                    v = v.isoformat()
                d[f.name] = v
            return d

        payload = {
            "generated_at": datetime.now().isoformat(),
            "num_emails": num_emails,
            "num_parsed": num_parsed,
            "digests": [
                {
                    "date": d.date.isoformat(),
                    "papers": [_paper_dict(p) for p in d.papers],
                }
                for d in digests
            ],
        }
        Path(output_json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        )
        print(f"Wrote JSON digest to {output_json}")

    if no_slack:
        print_digest(digests)
    else:
        send_digest_to_slack(
            digests,
            config,
            num_emails=num_emails,
            num_parsed=num_parsed,
        )

    if not no_cleanup:
        trashed = gmail.trash_emails(digests, verbose=verbose)
        print(f"Trashed {len(trashed)} processed emails.")
