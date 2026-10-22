"""Relevance judging and retrieval metrics."""

import pytest

from eval.metrics import gold_pages, judge, matches_evidence, mrr_at_k, ndcg_at_k, recall_at_k


def hit(source, page):
    return {"source": source, "page_or_url": page}


def test_evidence_ignores_spaces_and_case():
    assert matches_evidence("외국인유학생심리상담 안내", [["외국인 유학생 심리상담"]])
    assert matches_evidence("The ISIC card", [["isic", "CARD"]])
    assert not matches_evidence("The ISIC card", [["isic", "17,000"]])


def test_gold_pages_any_group():
    chunks = [{"text": "결핵검진 결과서", "source": "k.pdf", "page_or_url": 3},
              {"text": "Tuberculosis test", "source": "e.pdf", "page_or_url": 9},
              {"text": "unrelated", "source": "e.pdf", "page_or_url": 10}]
    assert gold_pages(chunks, [["결핵검진"], ["tuberculosis"]]) == {("k.pdf", "3"), ("e.pdf", "9")}


def test_judge_counts_each_gold_page_once():
    gold = {("a.pdf", "1")}
    assert judge([hit("a.pdf", 1), hit("a.pdf", 1), hit("b.pdf", 2)], gold) == [True, False, False]


def test_recall_and_mrr():
    flags = [False, False, True, False]
    assert recall_at_k(flags, 2) == 0.0
    assert recall_at_k(flags, 3) == 1.0
    assert mrr_at_k(flags, 10) == pytest.approx(1 / 3)
    assert mrr_at_k(flags, 2) == 0.0


def test_ndcg_perfect_and_partial():
    assert ndcg_at_k([True, True, False], n_gold=2, k=10) == pytest.approx(1.0)
    assert 0 < ndcg_at_k([False, True], n_gold=1, k=10) < 1
    assert ndcg_at_k([False, False], n_gold=1, k=10) == 0.0
