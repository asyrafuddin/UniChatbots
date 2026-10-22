#phase
# Phase 1: Setup and ingestion ✅

**Goal:** turn raw PDFs and web pages into clean, citable chunks.

- Python 3.12 venv (via `uv`), `config.yaml` for all settings
- Load PDFs (page by page) and web pages (with URL from `urls.csv`)
- Strip headers/footers (lines that repeat on ≥50% of pages)
- [[Chunking]]: 512 tokens, 10% overlap, using bge-m3's tokenizer
- Remove exact duplicates

**Result:** 26 PDFs → 1,680 chunks in `data/processed/chunks.jsonl`

```bash
python -m src.ingest.run_ingest
```

## What I learned
- 
