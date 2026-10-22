#concept
# RAG (Retrieval-Augmented Generation)

Instead of trusting the LLM's memory, first **retrieve** relevant passages from my documents, then ask the LLM to answer **only from them**, with citations.

My pipeline: question → retrieve top 30 → re-rank → top 5 → LLM → answer with [1], [2]

Related: [[Dense retrieval]], [[Cross-encoder re-ranker]], [[Chunking]]
