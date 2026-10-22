"""Evaluate retrievers on eval/retrieval_questions.jsonl and log the results.

Prints metrics overall and per question language (en / ms / ko / mixed), lists the questions
each retriever missed, and appends one row per retriever to eval/results.csv.

Usage (from the project root, with the .venv active):
    python -m eval.run_retrieval_eval --change "baseline: BM25 vs dense vs hybrid"
    python -m eval.run_retrieval_eval --kinds bm25 --no-log      # quick check, nothing written
    python -m eval.run_retrieval_eval --kinds dense --rerank     # dense vs dense + cross-encoder
"""

import argparse
import csv
import time
from datetime import date
from statistics import mean

from datasets import load_dataset
from tqdm import tqdm

from eval.metrics import gold_pages, judge, mrr_at_k, ndcg_at_k, recall_at_k
from src.config import load_config, resolve_path
from src.retrieve.base import load_chunks
from src.retrieve.build import KINDS, build_retrievers, with_reranking

LANGUAGES = ("en", "ms", "ko", "mixed")


def load_questions(cfg: dict, chunks: list[dict]) -> list[dict]:
    """Load the eval questions with HF `datasets` and attach each one's gold pages."""
    ds = load_dataset("json", data_files=str(resolve_path(cfg["eval"]["retrieval_questions"])), split="train")
    questions = [dict(row, gold=gold_pages(chunks, row["evidence"])) for row in ds]
    empty = [q["id"] for q in questions if not q["gold"]]
    if empty:
        raise ValueError(f"Evidence matches no chunk for: {empty} — fix eval/retrieval_questions.jsonl")
    return questions


def score_question(hits: list[dict], gold: set, cfg: dict) -> dict:
    """All metrics for one question's ranked hits."""
    e = cfg["eval"]
    flags = judge(hits, gold)
    scores = {f"R@{k}": recall_at_k(flags, k) for k in e["recall_ks"]}
    scores[f"MRR@{e['mrr_k']}"] = mrr_at_k(flags, e["mrr_k"])
    scores[f"NDCG@{e['ndcg_k']}"] = ndcg_at_k(flags, len(gold), e["ndcg_k"])
    return scores


def average(rows: list[dict]) -> dict:
    """Mean of each metric over a list of per-question score dicts."""
    return {m: round(mean(r[m] for r in rows), 3) for m in rows[0]} if rows else {}


def evaluate(retriever, questions: list[dict], cfg: dict) -> dict:
    """Run one retriever over all questions; return overall + per-language averages, misses and timing."""
    top_k = max(cfg["eval"]["recall_ks"])
    per_q, start = [], time.perf_counter()
    for q in tqdm(questions, desc=retriever.name, unit="q"):
        per_q.append({"q": q, "scores": score_question(retriever.search(q["question"], top_k), q["gold"], cfg)})
    seconds = time.perf_counter() - start
    report = {"all": average([p["scores"] for p in per_q])}
    for lang in LANGUAGES:
        report[lang] = average([p["scores"] for p in per_q if p["q"]["language"] == lang])
    misses = [p["q"] for p in per_q if p["scores"][f"R@{top_k}"] == 0]
    return {"report": report, "misses": misses, "ms_per_query": round(1000 * seconds / len(questions), 1)}


def print_report(name: str, result: dict, questions: list[dict]) -> None:
    """Print a metrics table (rows = all + each language) and the missed questions."""
    report = result["report"]
    metrics = list(report["all"])
    counts = {"all": len(questions), **{l: sum(q["language"] == l for q in questions) for l in LANGUAGES}}
    print(f"\n=== {name}  ({result['ms_per_query']} ms/query) ===")
    print(f"{'lang':<7}{'n':>4}" + "".join(f"{m:>10}" for m in metrics))
    for lang, scores in report.items():
        if scores:
            print(f"{lang:<7}{counts[lang]:>4}" + "".join(f"{scores[m]:>10.3f}" for m in metrics))
    top_k = max(q for q in [int(m[2:]) for m in metrics if m.startswith("R@")])
    print(f"Missed (no correct page in top {top_k}): " +
          (", ".join(f"{q['id']} {q['question']!r}" for q in result["misses"]) or "none"))


def settings_string(cfg: dict, kind: str, n_questions: int) -> str:
    """The settings that matter for this retriever, as one compact string for results.csv."""
    r, base = cfg["retrieval"], kind.split("+")[0]
    parts = [f"retriever={kind}", f"chunks={cfg['chunking']['max_tokens']}tok/{cfg['chunking']['overlap_ratio']}ovl",
             f"questions={n_questions}"]
    if base in ("dense", "hybrid") or kind.endswith("+rerank"):
        parts.append(f"dtype={r['dtype']} on {r['device']}")
    if base in ("dense", "hybrid"):
        parts.append(f"embedder={cfg['embedding']['model']}")
    if base in ("bm25", "hybrid"):
        parts.append(f"bm25 k1={r['bm25_k1']} b={r['bm25_b']} subword-tokens")
    if base == "hybrid":
        parts.append(f"RRF k={r['rrf_k']} candidates={r['candidate_k']}")
    if kind.endswith("+rerank"):
        rr = cfg["reranker"]
        parts.append(f"reranker={rr['model']} over top {r['top_k']} (max_length={rr['max_length']})")
    return "; ".join(parts)


def metrics_string(report: dict) -> str:
    """e.g. 'all: R@5=0.8 … | en: … | ms: …' for results.csv."""
    return " | ".join(f"{lang}: " + " ".join(f"{m}={v}" for m, v in scores.items())
                      for lang, scores in report.items() if scores)


def append_results(cfg: dict, rows: list[dict]) -> None:
    """Append rows (date, change, settings, metrics) to eval/results.csv, writing the header if new."""
    path = resolve_path(cfg["eval"]["results_csv"])
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "change", "settings", "metrics"])
        if new:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Evaluate retrievers")
    parser.add_argument("--kinds", nargs="+", choices=KINDS, default=list(KINDS))
    parser.add_argument("--change", default="retrieval eval", help="what changed (goes into results.csv)")
    parser.add_argument("--rerank", action="store_true", help="also evaluate each retriever + the cross-encoder")
    parser.add_argument("--reranker-model", default=None, help="override reranker.model (HF Hub model ID)")
    parser.add_argument("--no-log", action="store_true", help="don't append to results.csv")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.reranker_model:
        cfg["reranker"]["model"] = args.reranker_model
    chunks = load_chunks(resolve_path(cfg["paths"]["chunks_out"]))
    questions = load_questions(cfg, chunks)
    print(f"{len(questions)} questions, {len(chunks)} chunks; "
          f"avg gold pages per question: {mean(len(q['gold']) for q in questions):.1f}")

    retrievers = build_retrievers(cfg, tuple(args.kinds), chunks=chunks)
    if args.rerank:
        retrievers |= with_reranking(cfg, retrievers)
    rows = []
    for kind, retriever in retrievers.items():
        result = evaluate(retriever, questions, cfg)
        print_report(kind, result, questions)
        rows.append({"date": date.today().isoformat(), "change": args.change,
                     "settings": settings_string(cfg, kind, len(questions)),
                     "metrics": metrics_string(result["report"])})
    if not args.no_log:
        append_results(cfg, rows)
        print(f"\nAppended {len(rows)} row(s) to {cfg['eval']['results_csv']}")


if __name__ == "__main__":
    main()
