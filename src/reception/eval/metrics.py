"""Metric functions used by the evaluation scripts."""

import re
from collections.abc import Sequence

import jiwer


def _norm_text(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def word_error_rate(references: list[str], hypotheses: list[str]) -> float:
    """Corpus WER after lower-casing and stripping punctuation."""
    return float(
        jiwer.wer([_norm_text(r) for r in references], [_norm_text(h) for h in hypotheses])
    )


def _norm_fact(s: str) -> str:
    return re.sub(r"[\s,]+", " ", s.lower()).strip()


def facts_present(text: str, facts: Sequence[str]) -> tuple[bool, list[str]]:
    """Whether every required fact appears in ``text`` (case/comma/space-insensitive).

    Returns:
        (all present, missing facts)
    """
    hay = _norm_fact(text)
    missing = [str(f) for f in facts if _norm_fact(str(f)) not in hay]
    return not missing, missing


def retrieval_scores(
    ranked: list[list[str]], gold: list[list[str]], ks: Sequence[int] = (1, 3, 5)
) -> dict[str, float]:
    """Precision@k, hit-rate@k and MRR; a chunk id is relevant if it starts with a gold prefix.

    Args:
        ranked: Retrieved chunk ids per query, best first.
        gold: Gold id prefixes per query.
        ks: Cut-offs.

    Returns:
        ``p@k`` (relevant in top k / k), ``hit@k`` (any relevant in top k), ``mrr``.
    """
    out: dict[str, float] = {}
    n = len(ranked)

    def rel(cid: str, g: list[str]) -> bool:
        return any(cid.startswith(p) for p in g)

    for k in ks:
        out[f"p@{k}"] = (
            sum(sum(rel(c, g) for c in r[:k]) / k for r, g in zip(ranked, gold, strict=True)) / n
        )
        out[f"hit@{k}"] = (
            sum(any(rel(c, g) for c in r[:k]) for r, g in zip(ranked, gold, strict=True)) / n
        )
    rr = []
    for r, g in zip(ranked, gold, strict=True):
        rank = next((i + 1 for i, c in enumerate(r) if rel(c, g)), None)
        rr.append(1 / rank if rank else 0.0)
    out["mrr"] = sum(rr) / n
    return out


def detection_pr(predicted: list[bool], actual: list[bool]) -> tuple[float, float, float]:
    """Event-level precision, recall and F1."""
    tp = sum(p and a for p, a in zip(predicted, actual, strict=True))
    fp = sum(p and not a for p, a in zip(predicted, actual, strict=True))
    fn = sum(a and not p for p, a in zip(predicted, actual, strict=True))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f1


def sus_score(answers: Sequence[int]) -> float:
    """System Usability Scale (10 answers, 1-5) -> 0-100.

    Raises:
        ValueError: Not exactly ten answers in 1..5.
    """
    if len(answers) != 10 or not all(1 <= a <= 5 for a in answers):
        raise ValueError("SUS needs ten answers between 1 and 5")
    odd = sum(a - 1 for a in answers[0::2])
    even = sum(5 - a for a in answers[1::2])
    return (odd + even) * 2.5
