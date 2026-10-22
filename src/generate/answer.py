"""Question → retrieve + re-rank → LLM → answer with citations. The function the API calls."""

import re

from src.generate.llm import chat
from src.generate.prompt import NOT_FOUND_MARKER, build_messages

CITATION = re.compile(r"(\s*)\[(\d+)\]")  # group 1 = space before the marker, removed with it


def renumber_citations(answer: str, hits: list[dict]) -> tuple[str, list[dict]]:
    """Keep only the sources the answer cites, numbered 1, 2, … in order of first mention.

    The model sees 5 sources but may cite e.g. only [3] and [5]; the website then shows those two
    as [1] and [2]. Numbers that don't match a source are removed.
    """
    order: list[int] = []
    for m in CITATION.finditer(answer):
        n = int(m.group(2))
        if 1 <= n <= len(hits) and n not in order:
            order.append(n)
    new_number = {old: new for new, old in enumerate(order, start=1)}

    def replace(m: re.Match) -> str:
        n = int(m.group(2))
        return f"{m.group(1)}[{new_number[n]}]" if n in new_number else ""

    return CITATION.sub(replace, answer).strip(), [hits[n - 1] for n in order]


def citation_fields(hit: dict) -> dict:
    """Only the fields the website needs (same shape as Citation in web/src/types.ts)."""
    return {k: hit[k] for k in ("id", "source", "page_or_url", "section")}


def answer_question(question: str, retriever, llm_client, cfg: dict) -> dict:
    """Retrieve the top sources, ask the LLM, and return {answer, citations, found, model}."""
    hits = retriever.search(question, cfg["reranker"]["top_n"])
    reply = chat(llm_client, build_messages(question, hits), cfg)
    if reply.startswith(NOT_FOUND_MARKER) or not hits:
        answer = reply.removeprefix(NOT_FOUND_MARKER).strip()
        return {"answer": CITATION.sub("", answer).strip(), "citations": [], "found": False,
                "model": cfg["llm"]["model"]}
    answer, cited = renumber_citations(reply, hits)
    return {"answer": answer, "citations": [citation_fields(h) for h in cited], "found": True,
            "model": cfg["llm"]["model"]}
