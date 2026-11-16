"""Hallucination guard: every checkable claim must appear in the cited passages."""

import re
from dataclasses import dataclass, field

from reception.rag.index import Chunk

CITATION_RE = re.compile(r"\[([a-z]+:[^\]\s]+)\]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"https?://\S+|www\.\S+")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_ROOM = re.compile(r"\bc\d{3}\b", re.IGNORECASE)


@dataclass
class VerifyResult:
    """Outcome of verification with human-readable reasons."""

    ok: bool
    reasons: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    return re.sub(r"[,\s]", "", text.lower())


def strip_citations(answer: str) -> str:
    """Remove ``[id]`` markers and tidy spacing."""
    text = CITATION_RE.sub("", answer)
    text = re.sub(r"\s+([.,;!?])", r"\1", text)
    return " ".join(text.split())


def verify(answer: str, cited: list[Chunk]) -> VerifyResult:
    """Check an LLM answer against the passages it was given.

    Rules: at least one citation; every citation refers to a provided passage; every
    number, email, URL and room code in the answer appears in the cited passages.

    Args:
        answer: Raw LLM answer with ``[chunk-id]`` citations.
        cited: Passages the model was allowed to use.

    Returns:
        ``ok`` plus the reasons for any rejection.
    """
    reasons: list[str] = []
    by_id = {c.id: c for c in cited}
    ids = CITATION_RE.findall(answer)
    if not ids:
        reasons.append("no citation")
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        reasons.append(f"cites unknown passages {unknown}")
    support = _norm(" ".join(by_id[i].text for i in ids if i in by_id))
    body = CITATION_RE.sub(" ", answer)
    for pattern, kind in ((_URL, "url"), (_EMAIL, "email")):
        for m in pattern.findall(body):
            if _norm(m.rstrip(".")) not in support:
                reasons.append(f"unsupported {kind} {m}")
        body = pattern.sub(" ", body)
    for m in _ROOM.findall(body):
        if _norm(m) not in support:
            reasons.append(f"unsupported room {m}")
    for m in _NUMBER.findall(body):
        if _norm(m.rstrip(".,")) not in support:
            reasons.append(f"unsupported number {m}")
    return VerifyResult(ok=not reasons, reasons=reasons)
