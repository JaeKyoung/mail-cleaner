import click

from larklab.cli.common import CONTEXT_SETTINGS
from larklab.cli.digest import digest
from larklab.cli.io import export_papers, import_papers, rebuild_embeddings
from larklab.cli.paper import (
    add_paper,
    check_papers,
    delete_paper,
    edit_paper,
    list_papers,
    search_paper,
)


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """LarkLab - Scholar paper digest and management"""


cli.add_command(digest)
cli.add_command(add_paper)
cli.add_command(edit_paper)
cli.add_command(check_papers)
cli.add_command(delete_paper)
cli.add_command(list_papers)
cli.add_command(search_paper)
cli.add_command(export_papers)
cli.add_command(import_papers)
cli.add_command(rebuild_embeddings)
