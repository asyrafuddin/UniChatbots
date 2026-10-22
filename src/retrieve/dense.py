"""Dense (semantic) search: embed chunks and questions with a sentence-transformers model, search with FAISS.

Because the embedding model is multilingual, a Malay question and a Korean passage with the
same meaning end up close together — this is what makes cross-lingual retrieval work.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from src.retrieve.base import make_hits


def pick_device(setting: str) -> str:
    """Resolve "auto" to mps (Apple GPU), cuda or cpu; any other value is used as given."""
    if setting != "auto":
        return setting
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


def pick_dtype(setting: str, device: str):
    """The torch dtype to load models in; half precision is only used on a GPU (mps/cuda)."""
    import torch

    return torch.float32 if device == "cpu" else getattr(torch, setting)


def load_embedder(model_name: str, device: str, dtype):
    """Load a sentence-transformers model from the HF Hub (cached locally after the first download)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device=device, model_kwargs={"dtype": dtype})


def embed(model, texts: list[str], batch_size: int, progress: bool = False) -> np.ndarray:
    """Embed texts as unit-length float32 vectors, so inner product = cosine similarity."""
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=progress)
    return np.asarray(vectors, dtype="float32")


def chunks_fingerprint(chunks: list[dict]) -> str:
    """A short hash of the chunk ids and texts — changes whenever chunks.jsonl changes."""
    h = hashlib.sha256()
    for c in chunks:
        h.update(c["id"].encode() + b"\0" + c["text"].encode() + b"\0")
    return h.hexdigest()[:16]


def build_index(chunks: list[dict], model, batch_size: int):
    """Embed every chunk and put the vectors in an exact (brute-force) FAISS inner-product index."""
    import faiss

    vectors = embed(model, [c["text"] for c in chunks], batch_size, progress=True)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def save_index(index, index_dir: Path, meta: dict) -> None:
    """Write the FAISS index and a small JSON file describing what it was built from."""
    import faiss

    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "dense.faiss"))
    (index_dir / "dense_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_index_if_fresh(index_dir: Path, meta: dict):
    """Return the saved index if it was built from the same model and chunks, else None."""
    import faiss

    meta_path, index_path = index_dir / "dense_meta.json", index_dir / "dense.faiss"
    if not (meta_path.exists() and index_path.exists()):
        return None
    if json.loads(meta_path.read_text(encoding="utf-8")) != meta:
        return None
    return faiss.read_index(str(index_path))


class DenseRetriever:
    """Finds chunks whose embedding is most similar to the question's embedding."""

    name = "dense"

    def __init__(self, chunks: list[dict], model, index):
        self.chunks = chunks
        self.model = model
        self.index = index

    def search(self, query: str, top_k: int) -> list[dict]:
        """Embed the query and return the top_k nearest chunks."""
        scores, ids = self.index.search(embed(self.model, [query], batch_size=1), top_k)
        keep = ids[0] >= 0  # FAISS pads with -1 when there are fewer than top_k chunks
        return make_hits(self.chunks, ids[0][keep].tolist(), scores[0][keep].tolist())
