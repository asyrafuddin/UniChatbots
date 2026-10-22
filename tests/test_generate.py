"""Prompt building, citation renumbering and the answer flow, with a fake LLM (no HF calls)."""

from types import SimpleNamespace

from src.generate.answer import answer_question, renumber_citations
from src.generate.llm import strip_thinking
from src.generate.prompt import build_messages

HITS = [
    {"id": f"c{i}", "text": f"text {i}", "source": "handbook.pdf", "page_or_url": i, "section": f"s{i}"}
    for i in range(1, 6)
]


class FakeRetriever:
    def search(self, query, top_k):
        return HITS[:top_k]


class FakeLLM:
    """Mimics InferenceClient.chat_completion's response shape."""

    def __init__(self, reply):
        self.reply = reply
        self.messages = None

    def chat_completion(self, messages, **_):
        self.messages = messages
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])


def test_messages_number_sources_and_include_question():
    messages = build_messages("Bila boleh apply asrama?", HITS[:2])
    assert messages[0]["role"] == "system"
    user = messages[1]["content"]
    assert "[1] handbook.pdf, page 1 — s1" in user and "[2] handbook.pdf, page 2" in user
    assert user.endswith("Bila boleh apply asrama?")


def test_url_sources_shown_without_page_word():
    hit = {**HITS[0], "page_or_url": "https://example.com/fees"}
    assert "[1] handbook.pdf, https://example.com/fees" in build_messages("q", [hit])[1]["content"]


def test_renumber_keeps_cited_sources_in_order():
    answer, cited = renumber_citations("A [3]. B [5][3]. C [9].", HITS)
    assert answer == "A [1]. B [2][1]. C."
    assert [h["id"] for h in cited] == ["c3", "c5"]


def test_strip_thinking():
    assert strip_thinking("<think>reasoning…</think>\nAnswer [1]") == "Answer [1]"


def test_answer_with_citations(cfg):
    llm = FakeLLM("Permohonan asrama dibuka pada Januari dan Julai [2].")
    result = answer_question("Bila boleh apply asrama?", FakeRetriever(), llm, cfg)
    assert result["found"] is True
    assert result["answer"].endswith("[1].")
    assert result["citations"] == [{"id": "c2", "source": "handbook.pdf", "page_or_url": 2, "section": "s2"}]
    assert "text 5" in llm.messages[1]["content"]  # top_n = 5 sources were sent


def test_not_found_has_no_citations(cfg):
    llm = FakeLLM("NOT_FOUND: Dokumen rasmi tidak menyebut perkara ini [1].")
    result = answer_question("Siapa rektor?", FakeRetriever(), llm, cfg)
    assert result == {"answer": "Dokumen rasmi tidak menyebut perkara ini.", "citations": [],
                      "found": False, "model": cfg["llm"]["model"]}


def test_empty_llm_reply_raises(cfg):
    import pytest

    with pytest.raises(RuntimeError, match="no answer"):
        answer_question("q", FakeRetriever(), FakeLLM(""), cfg)
