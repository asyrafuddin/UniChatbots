"""Hybrid search: merge BM25 and dense rankings with Reciprocal Rank Fusion (RRF).

BM25 and dense scores are on different scales, so RRF ignores scores and uses only ranks:
each chunk gets sum(1 / (rrf_k + rank)) over the lists it appears in.
"""

from src.retrieve.base import Retriever


def reciprocal_rank_fusion(rankings: list[list[dict]], rrf_k: int) -> list[dict]:
    """Fuse several ranked hit lists into one, best first. The returned "score" is the RRF score."""
    fused: dict[str, float] = {}
    first_seen: dict[str, dict] = {}
    for hits in rankings:
        for hit in hits:
            fused[hit["id"]] = fused.get(hit["id"], 0.0) + 1.0 / (rrf_k + hit["rank"])
            first_seen.setdefault(hit["id"], hit)
    order = sorted(fused, key=fused.get, reverse=True)
    return [{**first_seen[cid], "score": fused[cid], "rank": rank}
            for rank, cid in enumerate(order, start=1)]


class HybridRetriever:
    """Runs several retrievers and fuses their results with RRF."""

    name = "hybrid"

    def __init__(self, retrievers: list[Retriever], rrf_k: int, candidate_k: int):
        self.retrievers = retrievers
        self.rrf_k = rrf_k
        self.candidate_k = candidate_k

    def search(self, query: str, top_k: int) -> list[dict]:
        """Take candidate_k results from each retriever, fuse, return the top_k."""
        rankings = [r.search(query, self.candidate_k) for r in self.retrievers]
        return reciprocal_rank_fusion(rankings, self.rrf_k)[:top_k]
