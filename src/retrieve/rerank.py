"""Re-ranking with a Hugging Face cross-encoder.

The embedder (bi-encoder) turns the question and each chunk into vectors SEPARATELY, which is fast
but approximate. A cross-encoder reads the question and one chunk TOGETHER and outputs a single
relevance score — much more accurate, but too slow for all 1,680 chunks. So: dense search picks
30 candidates, the cross-encoder re-scores those 30, and the best 5 go to the LLM.

Under the hood, sentence-transformers' CrossEncoder does roughly this with `transformers`:
    tokenizer = AutoTokenizer.from_pretrained(model_name)                    # download from the Hub
    model = AutoModelForSequenceClassification.from_pretrained(model_name)   # (cached in ~/.cache/huggingface)
    inputs = tokenizer(questions, passages, truncation=True, padding=True, return_tensors="pt")
    scores = model(**inputs).logits.squeeze(-1)                              # one number per (question, passage)
"""

from src.retrieve.base import Retriever


def load_cross_encoder(model_name: str, device: str, max_length: int, dtype):
    """Download (first time) and load a cross-encoder model from the HF Hub."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device=device, max_length=max_length, model_kwargs={"dtype": dtype})


class Reranker:
    """Re-scores retrieved hits with a cross-encoder and keeps the best ones."""

    def __init__(self, model, batch_size: int):
        self.model = model
        self.batch_size = batch_size

    def rerank(self, query: str, hits: list[dict], top_n: int) -> list[dict]:
        """Return the top_n hits by cross-encoder score; the retriever's rank and score are kept for comparison."""
        if not hits:
            return []
        scores = self.model.predict([(query, h["text"]) for h in hits], batch_size=self.batch_size,
                                    show_progress_bar=False)
        order = sorted(range(len(hits)), key=lambda i: scores[i], reverse=True)[:top_n]
        return [{**hits[i], "retrieval_rank": hits[i]["rank"], "retrieval_score": hits[i]["score"],
                 "score": float(scores[i]), "rank": rank}
                for rank, i in enumerate(order, start=1)]


class RerankedRetriever:
    """A retriever followed by a re-ranker — still has the same search() interface as the others."""

    def __init__(self, retriever: Retriever, reranker: Reranker, candidate_k: int):
        self.name = f"{retriever.name}+rerank"
        self.retriever = retriever
        self.reranker = reranker
        self.candidate_k = candidate_k

    def search(self, query: str, top_k: int) -> list[dict]:
        """Retrieve candidate_k hits, re-rank them, return the top_k."""
        return self.reranker.rerank(query, self.retriever.search(query, self.candidate_k), top_k)
