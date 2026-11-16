import pytest

from reception.eval.metrics import (
    detection_pr,
    facts_present,
    retrieval_scores,
    sus_score,
    word_error_rate,
)


def test_wer() -> None:
    assert word_error_rate(["where is room 806"], ["where is room 806"]) == 0.0
    assert word_error_rate(["where is room 806"], ["where is room 808"]) == pytest.approx(0.25)
    assert word_error_rate(["Where is the Xerox shop?"], ["where is the xerox shop"]) == 0.0


def test_facts_present_normalises() -> None:
    assert facts_present("Fee: 2,42,000 INR. Room 812!", ["2,42,000", "room 812"]) == (True, [])
    ok, missing = facts_present("Library is open", ["library", "basement"])
    assert not ok and missing == ["basement"]


def test_retrieval_scores() -> None:
    ranked = [["course:50:1", "course:54:0", "faq:x"], ["place:a", "place:b", "place:c"]]
    gold = [["course:50:"], ["place:c"]]
    s = retrieval_scores(ranked, gold, ks=(1, 3))
    assert s["p@1"] == pytest.approx(0.5)
    assert s["hit@3"] == pytest.approx(1.0)
    assert s["mrr"] == pytest.approx((1 + 1 / 3) / 2)


def test_detection_pr() -> None:
    p, r, f1 = detection_pr(predicted=[True, True, False, False], actual=[True, False, True, False])
    assert (p, r) == (0.5, 0.5) and f1 == pytest.approx(0.5)


def test_sus_score() -> None:
    assert sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0
    assert sus_score([3] * 10) == 50.0
    with pytest.raises(ValueError):
        sus_score([3] * 9)


def test_facts_present_accepts_numbers() -> None:
    assert facts_present("It offers 9 programmes", [9]) == (True, [])  # type: ignore[list-item]
