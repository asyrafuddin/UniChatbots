"""BM25 keyword search.

Korean glues particles onto words (학생증은, 학생증을 …), so splitting on spaces works badly.
Instead we split text into the embedding model's sub-word pieces, which handles Korean,
English and Malay with one tokenizer and no extra dependency.
"""

from collections.abc import Callable

import numpy as np
from rank_bm25 import BM25Okapi

from src.retrieve.base import make_hits

Tokenize = Callable[[str], list[str]]


def make_bm25_tokenizer(model_name: str) -> Tokenize:
    """Return a function that lowercases text and splits it into sub-word pieces (punctuation dropped)."""
    from transformers import AutoTokenizer  # imported here so other modules don't pay the cost

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize(text: str) -> list[str]:
        return [p for p in tokenizer.tokenize(text.lower()) if any(ch.isalnum() for ch in p)]

    return tokenize


class BM25Retriever:
    """Classic keyword ranking: rare words that appear often in a chunk score highest."""

    name = "bm25"

    def __init__(self, chunks: list[dict], tokenize: Tokenize, k1: float, b: float):
        self.chunks = chunks
        self.tokenize = tokenize
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks], k1=k1, b=b)

    def search(self, query: str, top_k: int) -> list[dict]:
        """Score every chunk against the query and return the top_k."""
        scores = self.bm25.get_scores(self.tokenize(query))
        top = np.argsort(-scores)[:top_k]
        return make_hits(self.chunks, top.tolist(), scores[top].tolist())
