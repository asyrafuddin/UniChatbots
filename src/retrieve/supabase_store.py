"""Keep chunks + their embeddings in Supabase (Postgres + pgvector) and search them there.

The question is still embedded locally with bge-m3 (Supabase can't run HF models);
Supabase stores the vectors and finds the nearest ones with the match_chunks SQL function
(see supabase/schema.sql).
"""

import numpy as np

from src.config import require_env
from src.retrieve.dense import embed


def get_supabase():
    """Connect with the SECRET key from .env — server-side only, never put it in the website."""
    from supabase import create_client

    key = require_env("SUPABASE_SECRET_KEY")
    if key.startswith("sb_publishable_"):
        raise RuntimeError("SUPABASE_SECRET_KEY holds the publishable key; the backend needs the secret key.")
    return create_client(require_env("SUPABASE_URL"), key)


def to_row(chunk: dict, vector: np.ndarray) -> dict:
    """One chunk as a database row (vector rounded to keep requests small)."""
    return {"id": chunk["id"], "text": chunk["text"], "source": chunk["source"],
            "page_or_url": str(chunk["page_or_url"]), "section": chunk["section"],
            "embedding": [round(float(x), 6) for x in vector]}


def from_row(row: dict) -> dict:
    """A database row back into chunk format: page numbers become ints again, URLs stay strings."""
    page = row["page_or_url"]
    return {"id": row["id"], "text": row["text"], "source": row["source"],
            "page_or_url": int(page) if page.isdigit() else page, "section": row["section"]}


def replace_chunks(client, table: str, chunks: list[dict], vectors: np.ndarray, batch_size: int) -> int:
    """Delete every row in the table, then insert all chunks in batches. Returns the row count afterwards."""
    client.table(table).delete().neq("id", "").execute()
    for start in range(0, len(chunks), batch_size):
        rows = [to_row(c, v) for c, v in zip(chunks[start:start + batch_size], vectors[start:start + batch_size])]
        client.table(table).insert(rows).execute()
        print(f"  uploaded {min(start + batch_size, len(chunks))}/{len(chunks)}")
    return client.table(table).select("id", count="exact").limit(1).execute().count


class SupabaseRetriever:
    """Dense search where the vectors live in Supabase instead of a local FAISS file."""

    name = "supabase"

    def __init__(self, client, model, match_function: str):
        self.client = client
        self.model = model
        self.match_function = match_function

    def search(self, query: str, top_k: int) -> list[dict]:
        """Embed the query locally, then ask Supabase for the top_k most similar chunks."""
        vector = embed(self.model, [query], batch_size=1)[0]
        rows = self.client.rpc(self.match_function, {"query_embedding": vector.tolist(),
                                                     "match_count": top_k}).execute().data
        return [{**from_row(r), "score": float(r["similarity"]), "rank": rank}
                for rank, r in enumerate(rows, start=1)]
