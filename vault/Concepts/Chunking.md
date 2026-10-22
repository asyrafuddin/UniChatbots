#concept
# Chunking

Split long documents into small pieces so retrieval can return just the relevant part.

- Size is measured in **tokens** (the embedding model's tokenizer), not characters
- **Overlap** (10%) carries a few sentences into the next chunk so facts on a boundary aren't lost
- Each chunk keeps its source, page/URL and section title, which is needed for citations

Used in [[Phase 1 - Setup and ingestion]].
