# Bilingual University Assistant (RAG)

A chatbot that answers students' questions about the university in **English and Malay**
(including mixed "rojak" questions), using only official documents and citing the source
and page/URL for every answer. Built with the Hugging Face ecosystem.

Pipeline (target): question → retrieve top 30 → re-rank → top 5 → LLM → answer with [1], [2] citations.

## Setup (macOS)

This project uses **Python 3.12**. Your system Python (3.15) is too new for some packages.
[`uv`](https://docs.astral.sh/uv/) installs 3.12 without needing Homebrew:

```bash
cd ~/UniChatbots
uv python install 3.12                 # one-time
uv venv --python 3.12 .venv            # create the virtual environment
source .venv/bin/activate              # run this in every new terminal
uv pip install -r requirements.txt     # or: pip install -r requirements.txt
cp .env.example .env                   # then paste your HF token into .env
```

## Adding documents

```
data/raw/pdfs/        ← put PDFs here
data/raw/web/         ← put saved .html / .txt pages here
data/raw/web/urls.csv ← one row per web file:  filename,url
```

Example `urls.csv`:
```
filename,url
fees_2026.html,https://www.myuni.edu.my/fees
```
Files in `data/raw/` are never edited by the code.

## Running

```bash
python -m pytest                                   # run all tests
python -m src.ingest.run_ingest                    # ingest data/raw → data/processed/chunks.jsonl

# dry run on a generated FAKE corpus
python -m src.ingest.fake_data data/sample_raw
python -m src.ingest.run_ingest --raw-dir data/sample_raw --out data/processed/sample_chunks.jsonl

# search the chunks (first run downloads BAAI/bge-m3 and builds the FAISS index, ~3 min on an M1)
python -m src.retrieve.search "Boleh repeat subject berapa kali?"
python -m src.retrieve.search "기숙사 신청 기간" --kind bm25 --top-k 3
python -m src.retrieve.search "Boleh repeat subject berapa kali?" --rerank    # + cross-encoder re-ranker

# evaluate BM25 / dense / hybrid on eval/retrieval_questions.jsonl (appends to eval/results.csv)
python -m eval.run_retrieval_eval --change "what you changed"
python -m eval.run_retrieval_eval --kinds dense --rerank          # dense vs dense + re-ranker

# ask one question end to end (retrieve → re-rank → LLM), no server needed
python -m src.generate.ask "Boleh repeat subject berapa kali?" --kind supabase
```

### Running the chatbot website (two terminals)

```bash
# terminal 1 — backend (loads bge-m3 + re-ranker, ~30 s); API docs at http://localhost:8000/docs
cd ~/UniChatbots && source .venv/bin/activate
uvicorn src.api.main:app --port 8000

# terminal 2 — website
cd ~/UniChatbots/web && npm run dev            # open http://localhost:5173
```

### Making the Vercel site work (backend on your Mac + free Cloudflare tunnel)

The website on Vercel is only static files; the backend runs on this Mac. A free Cloudflare quick tunnel
gives it a public `https://…trycloudflare.com` address, which changes every start, so the tunnel script
saves it in Supabase (`public_config` table) and the website looks it up there. No Vercel changes needed.

```bash
# terminal 1 — backend
cd ~/UniChatbots && source .venv/bin/activate && uvicorn src.api.main:app --port 8000
# terminal 2 — tunnel (needs cloudflared in ~/.local/bin); Ctrl+C removes the address again
cd ~/UniChatbots && source .venv/bin/activate && python -m src.api.tunnel
```
The site only answers while both are running and the Mac is awake. Leave `VITE_API_URL` unset in Vercel.
Rate limit: 5 questions/minute per visitor, 500/day in total (`api.rate_limit_*` in config.yaml).

(`space/` + `config.space.yaml` deploy the backend to a Hugging Face Docker Space instead with
`python -m space.deploy`, but that now requires HF PRO.)

### Supabase setup (once)
1. Supabase → SQL Editor → run [`supabase/schema.sql`](supabase/schema.sql) (tables `chunks`, `chats`, function `match_chunks`).
2. Put `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (the `sb_secret_…` key) in the root `.env` — never in `web/`.
3. `python -m src.retrieve.upload_supabase` — copies chunks + embeddings into `chunks` (re-run after every ingestion).

### LLM
`Qwen/Qwen3.8-27B` from the HF Hub, called with `huggingface_hub.InferenceClient`. Which key pays is set in
`config.yaml` (`llm.provider`, `llm.api_key_env`): currently Cerebras' free tier (`CEREBRAS_API_KEY` in `.env`).

The dense index is rebuilt automatically whenever `chunks.jsonl` or the embedding model changes.

### How retrieval is evaluated
`eval/retrieval_questions.jsonl` has 40 questions (10 each in en / ms / ko / mixed). Each one lists
**evidence phrases**; every page with a chunk containing them counts as a correct page, so all copies
of a fact count (the handbook has Korean, Chinese and English versions).
- **Recall@k**: share of questions with at least one correct page in the top k.
- **MRR@10**: average of 1/rank of the first correct hit (1.0 = always first).
- **NDCG@10**: rewards finding *more* of the correct pages, near the top.

All settings (model, chunk size, overlap, cleaning thresholds) are in `config.yaml`.

### Web frontend (React + TypeScript + Tailwind, in `web/`)

Needs Node.js 24 LTS (installed in `~/.local/node`, linked into `~/.local/bin`).

```bash
cd web
npm install        # first time only
npm run dev        # → http://localhost:5173  (Ctrl+C to stop)
npm run build      # type-check + production build into web/dist
```
Answers are a **demo placeholder** for now (`web/src/api.ts`); it will call the Python pipeline later.

## Project layout

| Folder | Purpose |
|---|---|
| `src/ingest/` | load PDFs/HTML → clean → chunk (by tokens) → de-duplicate → `chunks.jsonl` |
| `src/retrieve/` | BM25, dense (FAISS), hybrid (RRF), cross-encoder re-ranker — all behind one `search()` interface |
| `src/generate/` | prompt + LLM call (HF InferenceClient), answer with renumbered citations |
| `src/api/` | FastAPI backend the website calls; saves chats to Supabase |
| `web/` | React + Vite website (chat UI) |
| `supabase/` | database schema (pgvector chunks, chats) |
| `eval/` | test questions, metrics, `results.csv` |
| `train/` | embedding fine-tuning *(later)* |
| `tests/` | pytest tests, one file per module |

## Progress

- [x] **Phase 1: setup + ingestion.** Project skeleton, Python 3.12 venv, `config.yaml`, and an
  ingestion pipeline (PDF pages + web pages with URLs, header/footer removal, structure-aware
  token chunking with BAAI/bge-m3's tokenizer, exact-duplicate removal). Run on the real documents:
  26 PDFs → 1,680 chunks.
- [x] **Phase 2: retrieval + eval set.** BM25 (sub-word tokens), dense (bge-m3 + FAISS), hybrid (RRF),
  a 40-question eval set (en/ms/ko/mixed) and an eval script with per-language metrics.
  Dense is the default: best overall and the only one that handles Malay well (BM25 can't match
  Malay words to Korean text). Known issues for later: the pure-Malay question "Boleh repeat subject
  berapa kali?" finds the right passage only at rank 9 (a job for the re-ranker); the course-registration
  PDF repeats bold text 4× in the extracted chunks; the eval questions were drafted by Claude and still
  need a human review.
- [x] **Phase 3: re-ranker.** Hugging Face cross-encoder `BAAI/bge-reranker-v2-m3` re-scores dense search's
  top 30 and keeps the best 5. MRR@10 0.675 → 0.797, NDCG@10 0.559 → 0.652; R@5 stays 0.900.
  Both models run in float16 so they fit together in 8 GB RAM (float32 made the Mac swap and stall).
  Note: each language has only 10 questions, so one question changes a per-language score by 0.1.
- [x] **Phase 4: generation + website backend.** Qwen/Qwen3.8-27B (HF Inference Providers via Cerebras'
  free tier) answers only from the top 5 re-ranked chunks, in the question's language, with [n] citations
  renumbered to the sources it actually used, or says the documents don't cover it. Chunks + bge-m3 vectors
  live in Supabase (pgvector; same eval scores as local FAISS). A FastAPI server (`src/api/`) serves the
  React website (`web/`) and saves every question/answer to the Supabase `chats` table.
  Also fixed: duplicate chunk ids from Korean filenames (now unique and checked at ingestion).
  Known issues: answers take ~5–9 s (mostly the re-ranker on the M1); answer quality has only been checked
  by hand on a few questions — no automatic answer eval yet; adding the two 학칙 rule files made 2 eval
  questions miss (R@30 1.000 → 0.950); the 학칙 files have no URL in urls.csv.
- [ ] Phase 5: deploy (backend on HF Spaces, website hosting) + answer-quality eval
- [ ] Phase 6: fine-tune the embedder

## Experiment table

Every experiment also gets a row in `eval/results.csv`. All numbers come from actually running the eval scripts.

| Date | What changed | Settings | Recall@5 | MRR | NDCG@10 | Notes |
|---|---|---|---|---|---|---|
| 2026-10-23 | Baseline BM25 | sub-word tokens, k1=1.5 b=0.75 | 0.650 | 0.491 | 0.323 | Malay R@30 only 0.300 |
| 2026-10-23 | Baseline dense | BAAI/bge-m3, FAISS flat IP | **0.900** | **0.675** | **0.559** | R@30 = 1.000 in every language |
| 2026-10-23 | Baseline hybrid | BM25 + dense, RRF k=60, 30 candidates each | 0.800 | 0.653 | 0.478 | BM25 drags Malay down (R@5 0.500) |
| 2026-10-23 | Dense in float16 | same as dense, half precision on mps | 0.900 | 0.675 | 0.559 | identical to float32, half the memory |
| 2026-10-23 | **Dense + re-ranker** | BAAI/bge-reranker-v2-m3 (568M, fp16) over dense top 30 | 0.900 | **0.797** | **0.652** | Malay MRR 0.406 → 0.658; ~4.0 s/query on M1 |
| 2026-10-23 | Dense + small re-ranker | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (118M) | 0.900 | 0.734 | 0.626 | ~0.45 s/query (9× faster); weaker on ko/en |
| 2026-10-23 | Re-ingest (unique ids, +2 학칙 files → 1,707 chunks), dense | bge-m3, FAISS | 0.875 | 0.685 | 0.552 | 2 questions now miss top 30 |
| 2026-10-23 | Same, Supabase pgvector | bge-m3, Supabase `match_chunks` | 0.875 | 0.685 | 0.552 | identical to FAISS; +0.1 s/query |
| 2026-10-23 | **Supabase + re-ranker** (website setup) | + bge-reranker-v2-m3 fp16 | 0.875 | **0.795** | **0.668** | what the website uses |
