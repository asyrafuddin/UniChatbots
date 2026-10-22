#experiment
# Experiment log

Source of truth: `eval/results.csv`. Numbers here are copied from real eval runs.

| Date | Retriever | R@5 | MRR@10 | NDCG@10 | Malay MRR@10 | Notes |
|---|---|---|---|---|---|---|
| 2026-10-23 | [[BM25]] | 0.650 | 0.491 | 0.323 | 0.125 | Malay R@30 only 0.300 |
| 2026-10-23 | [[Dense retrieval]] | **0.900** | **0.675** | **0.559** | 0.406 | R@30 = 1.0 in every language |
| 2026-10-23 | [[Hybrid retrieval (RRF)]] | 0.800 | 0.653 | 0.478 | 0.247 | BM25 drags Malay down |
