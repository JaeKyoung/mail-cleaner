import click

from mail_cleaner.config import load_config
from mail_cleaner.output import print_digest
from mail_cleaner.pipeline import run_digest_pipeline
from mail_cleaner.slack_output import send_digest_to_slack


@click.command()
@click.option(
    "--max-results",
    default=50,
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
def main(max_results, days_back, model, no_summary, channel, query):
    """Mail Cleaner - Process Google Scholar alert emails and send digest to Slack"""
    config = load_config()
    config.max_results = max_results
    config.days_back = days_back
    config.ollama_model = model
    config.use_summary = not no_summary
    config.slack_channel = channel
    config.scholar_query = query

    digests, num_emails, num_parsed = run_digest_pipeline(config)

    print_digest(digests)
    send_digest_to_slack(
        digests,
        config,
        num_emails=num_emails,
        num_parsed=num_parsed,
    )


if __name__ == "__main__":
    main()
