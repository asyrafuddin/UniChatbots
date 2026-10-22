#phase
# Phase 2: Retrieval and eval ✅

**Goal:** find the right chunk for a question, and measure how well it works.

- [[BM25]] (keyword), [[Dense retrieval]] (bge-m3 + FAISS), [[Hybrid retrieval (RRF)]]
- 40 eval questions: 10 each in en / ms / ko / mixed
- Scored with [[Retrieval metrics]]

**Winner: dense.** R@5 0.900, MRR@10 0.675, NDCG@10 0.559 (see [[Experiment log]])
BM25 can't match Malay words to Korean text (Malay R@30 only 0.300).

## Known issues
- "Boleh repeat subject berapa kali?" → correct page only at rank 9 → [[Phase 3 - Re-ranker]]
- Course-registration PDF repeats bold text 4× in chunks
- Eval questions still need my review

## What I learned
- 
