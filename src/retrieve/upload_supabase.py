"""Upload chunks.jsonl + bge-m3 embeddings to the Supabase `chunks` table (replaces what's there).

Run this after supabase/schema.sql, and again whenever you re-run ingestion.

Usage (from the project root, with the .venv active):
    python -m src.retrieve.upload_supabase
"""

import argparse

from src.config import load_config, resolve_path
from src.retrieve.base import load_chunks
from src.retrieve.build import get_dense_index, load_configured_embedder
from src.retrieve.supabase_store import get_supabase, replace_chunks


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Upload chunks + embeddings to Supabase")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    s = cfg["supabase"]
    client = get_supabase()  # fail fast on missing keys, before loading the model
    chunks = load_chunks(resolve_path(cfg["paths"]["chunks_out"]))
    index = get_dense_index(chunks, load_configured_embedder(cfg), cfg)  # reuses the saved FAISS vectors
    vectors = index.reconstruct_n(0, index.ntotal)
    print(f"Uploading {len(chunks)} chunks to Supabase table '{s['chunks_table']}' …")
    count = replace_chunks(client, s["chunks_table"], chunks, vectors, s["upload_batch_size"])
    print(f"Done: the table now has {count} rows.")


if __name__ == "__main__":
    main()
