import click

from mail_cleaner.cleanup import trash_processed_emails
from mail_cleaner.config import load_config
from mail_cleaner.output import print_digest
from mail_cleaner.pipeline import run_digest_pipeline
from mail_cleaner.slack_output import send_digest_to_slack


@click.command()
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
    "--no-summary",
    is_flag=True,
    help="Use raw abstract instead of AI summary",
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
    "--cleanup",
    is_flag=True,
    help="Trash processed emails after output",
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
def main(max_results, days_back, model, no_summary, channel, query, no_fetch_abstracts, cleanup, verbose, batches, no_slack):
    """Mail Cleaner - Process Google Scholar alert emails and send digest to Slack"""
    config = load_config()
    config.max_results = max_results
    config.days_back = days_back
    config.ollama_model = model
    config.use_summary = not no_summary
    config.slack_channel = channel
    config.scholar_query = query

    digests, num_emails, num_parsed, service = run_digest_pipeline(
        config, fetch_abstracts=not no_fetch_abstracts, num_batches=batches,
    )

    print_digest(digests)
    if not no_slack:
        send_digest_to_slack(
            digests,
            config,
            num_emails=num_emails,
            num_parsed=num_parsed,
        )

    if cleanup:
        trashed = trash_processed_emails(service, digests, verbose=verbose)
        print(f"Trashed {len(trashed)} processed emails.")


if __name__ == "__main__":
    main()
