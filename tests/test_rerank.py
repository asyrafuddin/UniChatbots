"""Re-ranking logic with a fake cross-encoder (the real one is a 2 GB download)."""

from src.retrieve.rerank import RerankedRetriever, Reranker


class FakeCrossEncoder:
    """Scores a (question, passage) pair by how many question words the passage contains."""

    def predict(self, pairs, **_):
        return [sum(w in passage.lower() for w in question.lower().split()) for question, passage in pairs]


class FixedRetriever:
    """Always returns the same ranking, worst match first, so re-ranking has something to fix."""

    name = "fixed"

    def search(self, query, top_k):
        texts = ["nothing relevant", "dormitory", "dormitory application period"]
        return [{"id": str(i), "text": t, "score": 1.0 - i / 10, "rank": i + 1}
                for i, t in enumerate(texts)][:top_k]


def test_rerank_reorders_and_keeps_original_rank():
    hits = FixedRetriever().search("q", 3)
    out = Reranker(FakeCrossEncoder(), batch_size=2).rerank("dormitory application period", hits, top_n=2)
    assert [h["id"] for h in out] == ["2", "1"]
    assert [h["rank"] for h in out] == [1, 2]
    assert out[0]["retrieval_rank"] == 3


def test_rerank_empty_hits():
    assert Reranker(FakeCrossEncoder(), batch_size=2).rerank("q", [], top_n=5) == []


def test_reranked_retriever_has_search_interface():
    retriever = RerankedRetriever(FixedRetriever(), Reranker(FakeCrossEncoder(), 2), candidate_k=3)
    assert retriever.name == "fixed+rerank"
    assert retriever.search("dormitory application", top_k=1)[0]["id"] == "2"
