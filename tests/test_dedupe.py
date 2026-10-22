from src.ingest.dedupe import dedupe_chunks


def test_duplicates_removed_ignoring_case_and_spaces():
    chunks = [{"id": "a", "text": "Fees are RM100."},
              {"id": "b", "text": "fees  are\nRM100."},
              {"id": "c", "text": "Something else."}]
    kept, removed = dedupe_chunks(chunks)
    assert [c["id"] for c in kept] == ["a", "c"]
    assert [c["id"] for c in removed] == ["b"]
