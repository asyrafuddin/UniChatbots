"""Try a retriever from the command line.

Usage (from the project root, with the .venv active):
    python -m src.retrieve.search "Boleh repeat subject berapa kali?"
    python -m src.retrieve.search "기숙사 신청 기간" --kind bm25 --top-k 3
    python -m src.retrieve.search "Boleh repeat subject berapa kali?" --rerank   # dense top 30 → cross-encoder
    python -m src.retrieve.search "dorm" --rebuild      # force a fresh dense index
"""

import argparse

from src.config import load_config
from src.retrieve.build import KINDS, build_retrievers, with_reranking


def print_hits(hits: list[dict], preview_chars: int = 200) -> None:
    """Print rank, score, source, page/URL and the start of each hit's text."""
    for h in hits:
        text = " ".join(h["text"].split())
        moved = f" (was #{h['retrieval_rank']} before re-ranking)" if "retrieval_rank" in h else ""
        print(f"\n#{h['rank']}{moved}  score={h['score']:.4f}  {h['source']} | {h['page_or_url']} | {h['section'][:50]}")
        print(f"    {text[:preview_chars]}{'…' if len(text) > preview_chars else ''}")


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Search the document chunks")
    parser.add_argument("query")
    parser.add_argument("--kind", choices=KINDS, default=None, help="default: retrieval.default_kind in config.yaml")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rerank", action="store_true", help="re-rank the top results with the cross-encoder")
    parser.add_argument("--rebuild", action="store_true", help="rebuild the dense index first")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    kind = args.kind or cfg["retrieval"]["default_kind"]
    retrievers = build_retrievers(cfg, (kind,), rebuild=args.rebuild)
    if args.rerank:
        retrievers = with_reranking(cfg, retrievers)
    print_hits(next(iter(retrievers.values())).search(args.query, args.top_k))


if __name__ == "__main__":
    main()
