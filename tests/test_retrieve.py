"""Retrievers on a tiny corpus. Dense search uses a fake embedder so the test doesn't load bge-m3."""

import numpy as np
import pytest

from src.retrieve.bm25 import BM25Retriever, make_bm25_tokenizer
from src.retrieve.dense import (DenseRetriever, build_index, chunks_fingerprint, load_index_if_fresh,
                                save_index)
from src.retrieve.hybrid import HybridRetriever, reciprocal_rank_fusion

CHUNKS = [
    {"id": "a", "text": "기숙사 신청은 매년 1월과 7월에 합니다.", "source": "handbook.pdf", "page_or_url": 1, "section": "기숙사"},
    {"id": "b", "text": "The ISIC card costs KRW 17,000.", "source": "handbook.pdf", "page_or_url": 2, "section": "ISIC"},
    {"id": "c", "text": "Shuttle buses run between the station and campus.", "source": "guide.pdf", "page_or_url": 3, "section": "Bus"},
]


class FakeEmbedder:
    """Stands in for SentenceTransformer: one dimension per keyword, so 'meaning' is predictable."""

    KEYWORDS = ["기숙사", "isic", "bus"]

    def encode(self, texts, **_):
        vectors = np.array([[float(k in t.lower()) for k in self.KEYWORDS] + [0.01] for t in texts])
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


@pytest.fixture(scope="module")
def bm25(cfg):
    tokenize = make_bm25_tokenizer(cfg["embedding"]["model"])
    return BM25Retriever(CHUNKS, tokenize, k1=1.5, b=0.75)


@pytest.fixture
def dense():
    model = FakeEmbedder()
    return DenseRetriever(CHUNKS, model, build_index(CHUNKS, model, batch_size=2))


def test_bm25_tokenizer_shares_pieces_despite_korean_particles(cfg):
    tokenize = make_bm25_tokenizer(cfg["embedding"]["model"])
    # 기숙사 → 기/숙/사 but 기숙사는 → 기/숙/사는: most (not all) pieces still match
    plain, with_particle = set(tokenize("기숙사")), set(tokenize("기숙사는 어디예요?"))
    assert len(plain & with_particle) >= 2
    assert "?" not in with_particle


def test_bm25_finds_keyword_match(bm25):
    hits = bm25.search("기숙사는 언제 신청해요?", top_k=2)
    assert hits[0]["id"] == "a"
    assert [h["rank"] for h in hits] == [1, 2]


def test_dense_finds_similar_chunk(dense):
    hits = dense.search("isic price", top_k=3)
    assert hits[0]["id"] == "b"
    assert len(hits) == 3 and hits[0]["score"] >= hits[1]["score"]


def test_dense_top_k_larger_than_corpus(dense):
    assert len(dense.search("bus", top_k=10)) == len(CHUNKS)


def test_rrf_rewards_agreement():
    list1 = [{"id": "x", "rank": 1}, {"id": "y", "rank": 2}]
    list2 = [{"id": "y", "rank": 1}, {"id": "z", "rank": 2}]
    fused = reciprocal_rank_fusion([list1, list2], rrf_k=60)
    assert fused[0]["id"] == "y"  # in both lists → highest score
    assert fused[0]["score"] == pytest.approx(1 / 62 + 1 / 61)
    assert [h["rank"] for h in fused] == [1, 2, 3]


def test_hybrid_returns_top_k(bm25, dense):
    hybrid = HybridRetriever([bm25, dense], rrf_k=60, candidate_k=3)
    hits = hybrid.search("shuttle bus", top_k=2)
    assert len(hits) == 2 and hits[0]["id"] == "c"


def test_index_saved_and_reloaded_only_when_fresh(tmp_path):
    model = FakeEmbedder()
    meta = {"model": "fake", "fingerprint": chunks_fingerprint(CHUNKS)}
    save_index(build_index(CHUNKS, model, batch_size=2), tmp_path, meta)
    assert load_index_if_fresh(tmp_path, meta).ntotal == len(CHUNKS)
    changed = [*CHUNKS[:2], {**CHUNKS[2], "text": "edited"}]
    assert load_index_if_fresh(tmp_path, {**meta, "fingerprint": chunks_fingerprint(changed)}) is None
