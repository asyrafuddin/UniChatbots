#concept
# Cross-encoder re-ranker

A **bi-encoder** ([[Dense retrieval]]) embeds the question and the chunk separately: fast, but rough.
A **cross-encoder** reads the question and the chunk *together* and outputs one relevance score: slower, but much more accurate.

So: use dense to get 30 candidates quickly, then the cross-encoder to pick the best 5.

Model: `BAAI/bge-reranker-v2-m3`. Used in [[Phase 3 - Re-ranker]].
