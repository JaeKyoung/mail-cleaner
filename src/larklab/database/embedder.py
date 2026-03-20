import math

import ollama

from larklab.schemas import Paper, ScholarPaper

EMBED_MODEL = "qwen3-embedding:8b"
EMBED_DIM = 1024  # MRL truncation from 4096


def _truncate(vec: list[float]) -> list[float]:
    """Slice to EMBED_DIM and L2-normalize (Matryoshka)."""
    v = vec[:EMBED_DIM]
    norm = math.sqrt(sum(x * x for x in v))
    if norm > 0:
        v = [x / norm for x in v]
    return v


def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for the given text."""
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return _truncate(response["embeddings"][0])


def embed_paper(paper: Paper | ScholarPaper) -> list[float]:
    """Generate embedding from paper title + abstract."""
    text = f"{paper.title}\n{paper.abstract}"
    return generate_embedding(text)
