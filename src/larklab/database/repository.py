import json
import sqlite3

import sqlite_vec

from larklab.database.embedder import EMBED_DIM
from larklab.schemas import Paper

_PAPER_COLUMNS = "(title, authors, journal, abstract, url)"
_PAPER_PLACEHOLDERS = "(?, ?, ?, ?, ?)"
_DUPLICATE_THRESHOLD = 0.2  # cosine distance — below this = potentially same paper


class PaperRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def __enter__(self):
        self.init_db()
        return self

    def __exit__(self, *exc):
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def init_db(self) -> None:
        """Create tables if they don't exist."""
        self.conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS papers (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                title    TEXT NOT NULL UNIQUE,
                authors  TEXT NOT NULL,
                journal  TEXT NOT NULL,
                abstract TEXT NOT NULL,
                url      TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS papers_vec USING vec0 (
                paper_id INTEGER PRIMARY KEY,
                embedding FLOAT[{EMBED_DIM}] distance_metric=cosine
            );
        """)

    def exists(self, title: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM papers WHERE title = ?", (title,)
        ).fetchone()
        return row is not None

    def get_by_id(self, paper_id: int) -> Paper | None:
        """Get a single paper by ID."""
        row = self.conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
        return _row_to_paper(row) if row else None

    def find_similar_existing(self, paper: Paper) -> list[tuple[Paper, float]]:
        """Find existing papers similar by title or embedding.

        Returns list of (existing_paper, similarity_score).
        """
        matches: list[tuple[Paper, float]] = []

        if self.exists(paper.title):
            row = self.conn.execute(
                "SELECT * FROM papers WHERE title = ?", (paper.title,)
            ).fetchone()
            matches.append((_row_to_paper(row), 1.0))
            return matches

        if paper.embedding:
            results = self.search_similar(paper.embedding, limit=10)
            for existing, distance in results:
                if distance < _DUPLICATE_THRESHOLD:
                    matches.append((existing, 1 - distance))
        return matches

    def _next_id(self) -> int | None:
        """Find the smallest gap in IDs via SQL."""
        row = self.conn.execute(
            "SELECT t1.id + 1 AS gap FROM papers t1"
            " WHERE NOT EXISTS"
            " (SELECT 1 FROM papers t2 WHERE t2.id = t1.id + 1)"
            " ORDER BY t1.id LIMIT 1"
        ).fetchone()
        if (
            row
            and row["gap"]
            <= self.conn.execute("SELECT MAX(id) FROM papers").fetchone()[0]
        ):
            return row["gap"]
        # Check if id=1 is missing
        if not self.conn.execute("SELECT 1 FROM papers WHERE id = 1").fetchone():
            count = self.conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            if count > 0:
                return 1
        return None

    def save(self, paper: Paper) -> int:
        """Save a new paper. Fills ID gaps if any. Returns paper id."""
        gap_id = self._next_id()
        if gap_id is not None:
            self.conn.execute(
                "INSERT INTO papers (id, title, authors, journal,"
                " abstract, url) VALUES (?, ?, ?, ?, ?, ?)",
                (gap_id, *_paper_values(paper)),
            )
            paper_id = gap_id
        else:
            cur = self.conn.execute(
                f"INSERT INTO papers {_PAPER_COLUMNS} VALUES {_PAPER_PLACEHOLDERS}",
                _paper_values(paper),
            )
            paper_id = cur.lastrowid
        if paper.embedding:
            self._save_embedding(paper_id, paper.embedding)
        self.conn.commit()
        return paper_id

    def update(self, paper_id: int, paper: Paper) -> None:
        """Update metadata + embedding of existing paper."""
        self.conn.execute(
            """UPDATE papers
               SET title = ?, authors = ?, journal = ?,
                   abstract = ?, url = ?
               WHERE id = ?""",
            (*_paper_values(paper), paper_id),
        )
        self.conn.execute("DELETE FROM papers_vec WHERE paper_id = ?", (paper_id,))
        if paper.embedding:
            self._save_embedding(paper_id, paper.embedding)
        self.conn.commit()

    def delete(self, paper_id: int) -> bool:
        """Delete a paper by id. Returns True if deleted."""
        row = self.conn.execute(
            "SELECT 1 FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
        if row is None:
            return False
        self.conn.execute("DELETE FROM papers_vec WHERE paper_id = ?", (paper_id,))
        self.conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        self.conn.commit()
        return True

    def save_many(self, papers: list[Paper]) -> int:
        """Save multiple papers. Uses INSERT OR IGNORE for efficiency."""
        count = 0
        for paper in papers:
            try:
                cur = self.conn.execute(
                    f"INSERT OR IGNORE INTO papers {_PAPER_COLUMNS}"
                    f" VALUES {_PAPER_PLACEHOLDERS}",
                    _paper_values(paper),
                )
                if cur.rowcount > 0:
                    paper_id = cur.lastrowid
                    if paper.embedding:
                        self._save_embedding(paper_id, paper.embedding)
                    count += 1
            except sqlite3.IntegrityError:
                continue
        self.conn.commit()
        return count

    def get_papers(self) -> list[Paper]:
        rows = self.conn.execute("SELECT * FROM papers ORDER BY id").fetchall()
        return [_row_to_paper(r) for r in rows]

    def search_similar(
        self, embedding: list[float], limit: int = 5
    ) -> list[tuple[Paper, float]]:
        """Find papers most similar to the given embedding.

        Returns list of (paper, distance) tuples, sorted ascending.
        """
        rows = self.conn.execute(
            """SELECT p.*, v.distance
               FROM papers_vec v
               JOIN papers p ON p.id = v.paper_id
               WHERE v.embedding MATCH ?
                 AND k = ?
               ORDER BY v.distance""",
            (json.dumps(embedding), limit),
        ).fetchall()
        return [(_row_to_paper(r), r["distance"]) for r in rows]

    def rebuild_embeddings(self) -> int:
        """Re-embed all papers from their title + abstract."""
        papers = self.get_papers()
        self.conn.execute("DELETE FROM papers_vec")
        self.conn.commit()
        count = 0
        for paper in papers:
            paper.embedding = _embed(paper)
            self._save_embedding(paper.id, paper.embedding)
            count += 1
        self.conn.commit()
        return count

    def clear_and_import(self, papers: list[Paper]) -> int:
        """Delete all papers and import from list. Returns count."""
        self.conn.execute("DELETE FROM papers_vec")
        self.conn.execute("DELETE FROM papers")
        self.conn.commit()
        return self.save_many(papers)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _save_embedding(self, paper_id: int, embedding: list[float]) -> None:
        self.conn.execute(
            "INSERT INTO papers_vec (paper_id, embedding) VALUES (?, ?)",
            (paper_id, json.dumps(embedding)),
        )


def _embed(paper: Paper) -> list[float]:
    from larklab.database.embedder import embed_paper

    return embed_paper(paper)


def _paper_values(paper: Paper) -> tuple:
    return (
        paper.title,
        json.dumps(paper.authors),
        paper.journal,
        paper.abstract,
        paper.url,
    )


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        id=row["id"],
        title=row["title"],
        authors=json.loads(row["authors"]),
        journal=row["journal"],
        abstract=row["abstract"],
        url=row["url"],
        source_email_id="",
        received_at=None,
    )
