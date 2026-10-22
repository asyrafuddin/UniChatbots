"""Relevance judging and retrieval metrics (Recall@k, MRR@k, NDCG@k).

Relevance is judged per PAGE, not per chunk: each eval question lists evidence phrases, and
every page with a chunk containing them is a correct page. This survives re-chunking and gives
credit for each copy of a fact (e.g. the Korean, Chinese and English parts of the handbook).
"""

import math
import re


def squash(text: str) -> str:
    """Lowercase and remove all whitespace (one handbook version drops the spaces in Korean)."""
    return re.sub(r"\s+", "", text).lower()


def matches_evidence(text: str, evidence: list[list[str]]) -> bool:
    """True if the text contains every term of at least one evidence group."""
    text = squash(text)
    return any(all(squash(term) in text for term in group) for group in evidence)


def page_key(chunk: dict) -> tuple[str, str]:
    """(source, page or URL) — the unit we judge relevance on."""
    return chunk["source"], str(chunk["page_or_url"])


def gold_pages(chunks: list[dict], evidence: list[list[str]]) -> set[tuple[str, str]]:
    """All pages that contain a chunk matching the evidence."""
    return {page_key(c) for c in chunks if matches_evidence(c["text"], evidence)}


def judge(hits: list[dict], gold: set[tuple[str, str]]) -> list[bool]:
    """Mark each hit relevant if its page is gold — only the first hit per gold page counts."""
    seen: set[tuple[str, str]] = set()
    flags = []
    for hit in hits:
        key = page_key(hit)
        flags.append(key in gold and key not in seen)
        seen.add(key)
    return flags


def recall_at_k(flags: list[bool], k: int) -> float:
    """1.0 if at least one correct page is in the top k, else 0.0 (averaged over questions = Recall@k).

    We use this "found it at all" version because one correct passage is enough to answer;
    NDCG below rewards finding more of the copies.
    """
    return float(any(flags[:k]))


def mrr_at_k(flags: list[bool], k: int) -> float:
    """1 / rank of the first correct hit within the top k (0 if none)."""
    for rank, ok in enumerate(flags[:k], start=1):
        if ok:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(flags: list[bool], n_gold: int, k: int) -> float:
    """Normalised discounted cumulative gain: correct hits near the top count more; 1.0 is perfect."""
    dcg = sum(1.0 / math.log2(rank + 1) for rank, ok in enumerate(flags[:k], start=1) if ok)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(n_gold, k) + 1))
    return dcg / ideal if ideal else 0.0
