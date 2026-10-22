#phase #current
# Phase 3: Re-ranker ⏳

**Goal:** take dense top 30 → re-score with a [[Cross-encoder re-ranker]] → keep top 5.

- Model: `BAAI/bge-reranker-v2-m3` (multilingual, 568M params)
- Baseline to beat: R@5 0.900, MRR@10 0.675, NDCG@10 0.559; **Malay MRR@10 0.406**

## To do
- [ ] Review `eval/retrieval_questions.jsonl`
- [ ] Add a pure-Malay "repeat subject" question
- [ ] Run eval with re-ranker, log in [[Experiment log]]

## What I learned
- 
