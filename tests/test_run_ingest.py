import json

from src.ingest.fake_data import HEADER
from src.ingest.run_ingest import ingest


def test_full_pipeline_on_fake_corpus(fake_raw_dir, cfg, count, tmp_path):
    out = tmp_path / "chunks.jsonl"
    stats = ingest(cfg, count, raw_dir=fake_raw_dir, out_path=out)

    chunks = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert stats["chunks"] == len(chunks) > 0
    assert stats["pdf_pages"] == 3 and stats["web_docs"] == 3
    assert stats["duplicates_removed"] == 1  # the portal notice appears on two web pages
    for chunk in chunks:
        assert set(chunk) == {"id", "text", "source", "page_or_url", "section"}
        assert chunk["section"]
        assert HEADER not in chunk["text"]
        assert count(chunk["text"]) <= cfg["chunking"]["max_tokens"]


def test_duplicate_ids_are_rejected():
    import pytest

    from src.ingest.run_ingest import check_unique_ids

    check_unique_ids([{"id": "a"}, {"id": "b"}])
    with pytest.raises(ValueError, match="Duplicate chunk ids"):
        check_unique_ids([{"id": "a"}, {"id": "a"}])
