#concept
# Hybrid retrieval (Reciprocal Rank Fusion)

Merge two ranked lists (BM25 and dense) by adding `1 / (k + rank)` for each list a chunk appears in (k = 60).

In my eval it was **worse than dense alone**, because BM25's bad Malay results dragged it down.

See [[BM25]], [[Dense retrieval]], [[Experiment log]]
