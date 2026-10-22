#concept
# Dense retrieval

An embedding model turns text into a vector (a list of numbers) that captures **meaning**. Similar meanings get close vectors, even across languages.

- Model: `BAAI/bge-m3` (multilingual, via `sentence-transformers`)
- Index: FAISS (fast nearest-vector search)
- This is why a Malay question can find a Korean passage

Compare: [[BM25]] · Combined in [[Hybrid retrieval (RRF)]]
