"""Supabase row conversion, upload batching and search, with a fake client (no network)."""

from types import SimpleNamespace

import numpy as np

from src.retrieve.supabase_store import SupabaseRetriever, from_row, replace_chunks, to_row

CHUNK = {"id": "a", "text": "Dorm", "source": "h.pdf", "page_or_url": 7, "section": "Dormitory"}


class FakeQuery:
    """Records calls like client.table(t).insert(rows).execute() and returns canned data."""

    def __init__(self, log, data=None, count=None):
        self.log, self.data, self.count = log, data, count

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.log.append((name, args))
            return self
        return call

    def execute(self):
        return SimpleNamespace(data=self.data, count=self.count)


class FakeClient:
    def __init__(self, rpc_rows=None, count=0):
        self.log, self.rpc_rows, self.count = [], rpc_rows, count

    def table(self, name):
        return FakeQuery(self.log, count=self.count)

    def rpc(self, name, params):
        self.log.append(("rpc", (name, params)))
        return FakeQuery(self.log, data=self.rpc_rows)


class FakeEmbedder:
    def encode(self, texts, **_):
        return np.ones((len(texts), 4)) / 2


def test_row_round_trip_keeps_page_numbers_and_urls():
    row = to_row(CHUNK, np.array([0.1234567, 0.5]))
    assert row["page_or_url"] == "7" and row["embedding"] == [0.123457, 0.5]
    assert from_row(row) == CHUNK
    assert from_row({**row, "page_or_url": "https://x.kr/a"})["page_or_url"] == "https://x.kr/a"


def test_replace_chunks_deletes_then_inserts_in_batches():
    client = FakeClient(count=3)
    chunks = [{**CHUNK, "id": str(i)} for i in range(3)]
    count = replace_chunks(client, "chunks", chunks, np.zeros((3, 4)), batch_size=2)
    calls = [name for name, _ in client.log]
    assert calls[0] == "delete" and calls.count("insert") == 2 and count == 3


def test_search_calls_match_function_and_ranks_hits():
    rows = [{**to_row(CHUNK, np.zeros(4)), "similarity": 0.9}]
    client = FakeClient(rpc_rows=rows)
    hits = SupabaseRetriever(client, FakeEmbedder(), "match_chunks").search("dorm", top_k=3)
    name, params = client.log[0][1]
    assert name == "match_chunks" and params["match_count"] == 3 and len(params["query_embedding"]) == 4
    assert hits == [{**CHUNK, "score": 0.9, "rank": 1}]
