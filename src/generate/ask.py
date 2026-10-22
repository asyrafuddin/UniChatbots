"""Ask one question from the command line (no website or server needed).

Usage (from the project root, with the .venv active):
    python -m src.generate.ask "Boleh repeat subject berapa kali?"
    python -m src.generate.ask "기숙사 신청은 언제 해요?" --kind supabase
"""

import argparse
import time

from src.config import load_config
from src.generate.answer import answer_question
from src.generate.llm import make_llm_client
from src.retrieve.build import KINDS, build_retrievers, with_reranking


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Answer a question from the documents")
    parser.add_argument("question")
    parser.add_argument("--kind", choices=KINDS, default=None, help="default: retrieval.default_kind")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    kind = args.kind or cfg["retrieval"]["default_kind"]
    retriever = next(iter(with_reranking(cfg, build_retrievers(cfg, (kind,))).values()))
    start = time.perf_counter()
    result = answer_question(args.question, retriever, make_llm_client(cfg), cfg)
    print(f"\n{result['answer']}\n")
    for n, c in enumerate(result["citations"], start=1):
        print(f"[{n}] {c['source']} | {c['page_or_url']} | {c['section']}")
    print(f"\n(found={result['found']}, model={result['model']}, {time.perf_counter() - start:.1f}s)")


if __name__ == "__main__":
    main()
