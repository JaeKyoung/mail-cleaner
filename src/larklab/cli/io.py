import json
from pathlib import Path

import click

from larklab.cli.common import CONTEXT_SETTINGS
from larklab.config import PROJECT_ROOT, load_config
from larklab.database.embedder import embed_paper
from larklab.database.repository import PaperRepository
from larklab.schemas import Paper

_JSONS_DIR = PROJECT_ROOT / "data" / "jsons"


def _paper_to_dict(p: Paper) -> dict:
    return {
        "title": p.title,
        "authors": p.authors,
        "journal": p.journal,
        "abstract": p.abstract,
        "url": p.url,
    }


@click.command("db-export", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Output path (default: data/jsons/)",
)
@click.option(
    "--query",
    default=None,
    help="Export only papers matching keyword in title",
)
@click.option(
    "--md",
    is_flag=True,
    help="Export as Markdown (default: data/papers.md)",
)
def export_papers(output, query, md):
    """Export papers to individual JSONs or Markdown"""
    config = load_config()
    with PaperRepository(config.db_path) as repo:
        papers = repo.get_papers()

    if query:
        q = query.lower()
        papers = [p for p in papers if q in p.title.lower()]

    if md:
        out_path = Path(output) if output else PROJECT_ROOT / "data" / "papers.md"
        lines = [f"# Reference Papers ({len(papers)})\n"]
        for p in papers:
            authors_str = ", ".join(p.authors[:3])
            if len(p.authors) > 3:
                authors_str += " et al."
            lines.append(f"- [{p.title}]({p.url})")
            lines.append(f"  - {authors_str} — {p.journal}")
            lines.append("")
        out_path.write_text("\n".join(lines))
        print(f"Exported {len(papers)} papers to {out_path}")
    else:
        out_dir = Path(output) if output else _JSONS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        # Clean old files
        for f in out_dir.glob("*.json"):
            f.unlink()
        for p in papers:
            data = _paper_to_dict(p)
            path = out_dir / f"{p.id}.json"
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"Exported {len(papers)} papers to {out_dir}/")


@click.command("db-import", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--input",
    "input_path",
    default=None,
    type=click.Path(exists=True),
    help="Input path: directory of JSONs or single JSON file",
)
def import_papers(input_path):
    """Import papers from JSONs (replaces all existing data)"""
    in_path = Path(input_path) if input_path else _JSONS_DIR

    if in_path.is_dir():
        files = sorted(
            (f for f in in_path.glob("*.json") if f.stem.isdigit()),
            key=lambda f: int(f.stem),
        )
        data_list = []
        for f in files:
            data_list.append(json.loads(f.read_text()))
    elif in_path.is_file():
        raw = json.loads(in_path.read_text())
        data_list = raw if isinstance(raw, list) else [raw]
    else:
        print(f"Not found: {in_path}")
        return

    papers = []
    for item in data_list:
        papers.append(
            Paper(
                title=item["title"],
                authors=item["authors"],
                journal=item["journal"],
                abstract=item["abstract"],
                url=item["url"],
                source_email_id="",
                received_at=None,
            )
        )

    print(f"Read {len(papers)} papers from {in_path}")
    print("Generating embeddings...")
    for i, paper in enumerate(papers):
        print(f"  Embedding {i + 1}/{len(papers)}...")
        paper.embedding = embed_paper(paper)

    config = load_config()
    with PaperRepository(config.db_path) as repo:
        count = repo.clear_and_import(papers)
    print(f"Imported {count} papers.")


@click.command("db-rebuild", context_settings=CONTEXT_SETTINGS)
def rebuild_embeddings():
    """Re-generate all embeddings from stored title + abstract"""
    config = load_config()
    with PaperRepository(config.db_path) as repo:
        count = repo.rebuild_embeddings()
    print(f"Rebuilt embeddings for {count} papers.")
