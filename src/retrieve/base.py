"""Shared pieces for every retriever: the common interface, loading chunks, building hit lists."""

import json
from pathlib import Path
from typing import Protocol


class Retriever(Protocol):
    """Anything with a name and a search() method can be used as a retriever."""

    name: str

    def search(self, query: str, top_k: int) -> list[dict]:
        """Return up to top_k hits, best first. A hit is a chunk dict plus "score" and "rank"."""
        ...


def load_chunks(path: str | Path) -> list[dict]:
    """Read chunks.jsonl (one chunk per line) into a list of dicts."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def make_hits(chunks: list[dict], indices: list[int], scores: list[float]) -> list[dict]:
    """Turn (chunk index, score) pairs into hit dicts with a 1-based rank."""
    return [{**chunks[i], "score": float(s), "rank": rank}
            for rank, (i, s) in enumerate(zip(indices, scores), start=1)]
