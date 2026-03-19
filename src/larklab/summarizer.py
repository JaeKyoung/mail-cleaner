import ollama

from larklab.models import Paper

DEFAULT_MODEL = "qwen3:8b"


def summarize_abstract(paper: Paper, model: str = DEFAULT_MODEL) -> str:
    """Summarize a paper's abstract into 3 structured bullet points using a local LLM."""
    if not paper.abstract:
        return ""

    prompt = (
        "Summarize this paper as exactly 3 bullet points using '•'. "
        "No labels, no headers, no 'Why/How/Result' prefixes. Just the content.\n\n"
        "• Problem and motivation (1 sentence)\n"
        "• Specific model/algorithm/architecture, input representation, and technical novelty (1-2 sentences)\n"
        "• Main finding (1 sentence)\n\n"
        "Be technical. Never use vague phrases like 'AI algorithms' or 'advanced methods'. "
        "Name the exact technique. Always respond in English. "
        "Do NOT include numbers or metrics not explicitly in the abstract. "
        "Do not repeat the title. No preamble.\n\n"
        f"Title: {paper.title}\n"
        f"Abstract: {paper.abstract}"
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"num_predict": 1024},
    )

    return response["message"]["content"].strip()
