"""Run the ingestion pipeline: load → clean → chunk → de-duplicate → save → print stats.

Usage (from the project root, with the .venv active):
    python -m src.ingest.run_ingest
    python -m src.ingest.run_ingest --raw-dir data/sample_raw --out data/processed/sample_chunks.jsonl
"""

import argparse
import json
import logging
import random
from pathlib import Path
from statistics import mean

from src.config import load_config, resolve_path
from src.ingest.chunk import TokenCounter, chunk_records
from src.ingest.clean import clean_records
from src.ingest.dedupe import dedupe_chunks
from src.ingest.loaders import load_pdfs, load_web
from src.ingest.tokens import make_token_counter


def ingest(cfg: dict, count: TokenCounter, raw_dir: str | Path | None = None,
           out_path: str | Path | None = None) -> dict:
    """Run the whole pipeline, write chunks.jsonl and return a stats dict."""
    p = cfg["paths"]
    raw_dir = resolve_path(raw_dir or p["raw_dir"])
    out_path = resolve_path(out_path or p["chunks_out"])
    web_dir = raw_dir / p["web_subdir"]

    records = load_pdfs(raw_dir / p["pdf_subdir"], cfg) + load_web(web_dir, web_dir / p["urls_csv"])
    cleaned, header_patterns = clean_records(records, cfg)
    chunks, duplicates = dedupe_chunks(chunk_records(cleaned, cfg, count))
    save_jsonl(chunks, out_path)
    return compute_stats(records, chunks, duplicates, header_patterns, count, cfg, out_path)


def save_jsonl(chunks: list[dict], path: Path) -> None:
    """Write one JSON object per line (UTF-8, Malay characters kept readable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def compute_stats(records: list[dict], chunks: list[dict], duplicates: list[dict],
                  header_patterns: dict, count: TokenCounter, cfg: dict, out_path: Path) -> dict:
    """Collect the numbers printed at the end of a run."""
    lengths = [count(c["text"]) for c in chunks]
    rng = random.Random(cfg["stats"]["seed"])
    return {
        "pdf_docs": len({r["source"] for r in records if r["kind"] == "pdf"}),
        "pdf_pages": sum(r["kind"] == "pdf" for r in records),
        "web_docs": sum(r["kind"] == "web" for r in records),
        "chunks": len(chunks),
        "duplicates_removed": len(duplicates),
        "avg_tokens": round(mean(lengths), 1) if lengths else 0,
        "min_tokens": min(lengths, default=0),
        "max_tokens": max(lengths, default=0),
        "header_patterns": header_patterns,
        "samples": rng.sample(chunks, min(cfg["stats"]["sample_chunks"], len(chunks))),
        "out_path": str(out_path),
    }


def print_stats(stats: dict) -> None:
    """Print a human-readable summary of an ingestion run."""
    print("\n=== Ingestion stats ===")
    print(f"Documents : {stats['pdf_docs'] + stats['web_docs']} "
          f"({stats['pdf_docs']} PDF, {stats['web_docs']} web)")
    print(f"PDF pages : {stats['pdf_pages']}")
    print(f"Chunks    : {stats['chunks']}  (duplicates removed: {stats['duplicates_removed']})")
    print(f"Tokens/chunk: avg {stats['avg_tokens']}, min {stats['min_tokens']}, max {stats['max_tokens']}")
    print(f"Saved to  : {stats['out_path']}")
    print("\nHeader/footer patterns removed (digits shown as #):")
    for source, patterns in stats["header_patterns"].items():
        for pattern in sorted(patterns):
            print(f"  {source}: {pattern!r}")
    if not stats["header_patterns"]:
        print("  (none)")
    for i, chunk in enumerate(stats["samples"], start=1):
        print(f"\n--- Sample {i}: {chunk['id']} | {chunk['source']} | {chunk['page_or_url']} "
              f"| section: {chunk['section']!r}")
        print(chunk["text"][:600] + ("…" if len(chunk["text"]) > 600 else ""))


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Ingest raw documents into chunks.jsonl")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--raw-dir", default=None, help="override paths.raw_dir")
    parser.add_argument("--out", default=None, help="override paths.chunks_out")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    cfg = load_config(args.config)
    count = make_token_counter(cfg["embedding"]["model"])
    print_stats(ingest(cfg, count, args.raw_dir, args.out))


if __name__ == "__main__":
    main()
