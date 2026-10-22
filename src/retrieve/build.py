"""Build retrievers from config.yaml — the one place the rest of the project gets them from."""

import logging
import time

from src.config import resolve_path
from src.retrieve.base import Retriever, load_chunks
from src.retrieve.bm25 import BM25Retriever, make_bm25_tokenizer
from src.retrieve.dense import (DenseRetriever, build_index, chunks_fingerprint, load_embedder,
                                load_index_if_fresh, pick_device, pick_dtype, save_index)
from src.retrieve.hybrid import HybridRetriever
from src.retrieve.rerank import RerankedRetriever, Reranker, load_cross_encoder

KINDS = ("bm25", "dense", "hybrid")
log = logging.getLogger(__name__)


def get_dense_index(chunks: list[dict], model, cfg: dict, rebuild: bool = False):
    """Load the saved FAISS index, or build (and save) it if missing, stale or rebuild=True."""
    r = cfg["retrieval"]
    index_dir = resolve_path(r["index_dir"])
    meta = {"model": cfg["embedding"]["model"], "dtype": str(model.dtype), "chunks": len(chunks),
            "fingerprint": chunks_fingerprint(chunks)}
    index = None if rebuild else load_index_if_fresh(index_dir, meta)
    if index is None:
        print(f"Building dense index for {len(chunks)} chunks (one-off; saved to {index_dir}) …")
        start = time.perf_counter()
        index = build_index(chunks, model, r["embed_batch_size"])
        save_index(index, index_dir, meta)
        print(f"Dense index built in {time.perf_counter() - start:.0f}s")
    return index


def build_retrievers(cfg: dict, kinds: tuple[str, ...] = KINDS, chunks: list[dict] | None = None,
                     rebuild: bool = False) -> dict[str, Retriever]:
    """Return {kind: retriever} for the requested kinds, sharing one model and index between them."""
    unknown = set(kinds) - set(KINDS)
    if unknown:
        raise ValueError(f"Unknown retriever kind(s): {sorted(unknown)}; choose from {KINDS}")
    r, model_name = cfg["retrieval"], cfg["embedding"]["model"]
    chunks = chunks if chunks is not None else load_chunks(resolve_path(cfg["paths"]["chunks_out"]))

    built: dict[str, Retriever] = {}
    if {"bm25", "hybrid"} & set(kinds):
        built["bm25"] = BM25Retriever(chunks, make_bm25_tokenizer(model_name), r["bm25_k1"], r["bm25_b"])
    if {"dense", "hybrid"} & set(kinds):
        device = pick_device(r["device"])
        log.info("Embedding model %s on %s", model_name, device)
        model = load_embedder(model_name, device, pick_dtype(r["dtype"], device))
        built["dense"] = DenseRetriever(chunks, model, get_dense_index(chunks, model, cfg, rebuild))
    if "hybrid" in kinds:
        built["hybrid"] = HybridRetriever([built["bm25"], built["dense"]], r["rrf_k"], r["candidate_k"])
    return {k: built[k] for k in kinds}


def build_reranker(cfg: dict) -> Reranker:
    """Load the cross-encoder named in config.yaml (reranker.model)."""
    rr = cfg["reranker"]
    device = pick_device(cfg["retrieval"]["device"])
    log.info("Re-ranker %s on %s", rr["model"], device)
    model = load_cross_encoder(rr["model"], device, rr["max_length"], pick_dtype(cfg["retrieval"]["dtype"], device))
    return Reranker(model, rr["batch_size"])


def with_reranking(cfg: dict, retrievers: dict[str, Retriever]) -> dict[str, Retriever]:
    """Wrap each retriever so its top retrieval.top_k results are re-ranked; keys become e.g. "dense+rerank"."""
    reranker = build_reranker(cfg)
    wrapped = [RerankedRetriever(r, reranker, cfg["retrieval"]["top_k"]) for r in retrievers.values()]
    return {w.name: w for w in wrapped}
