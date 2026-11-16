"""Grounded answers: retrieve -> gate -> compose with an LLM -> verify."""

import re

from reception.config import AppConfig
from reception.dialogue.handover import handover_response
from reception.kb.loader import KnowledgeBase
from reception.llm.base import LLM, LLMUnavailable
from reception.rag.index import HybridIndex
from reception.rag.verify import CITATION_RE, strip_citations, verify
from reception.types import Card, IntentName, Link, Response

SYSTEM_PROMPT = (
    "You are the reception assistant for CHRIST University's Central Block. "
    "Answer ONLY using the passages provided. Do not add any fact, number, date, name, "
    "room, phone number, email or link that is not written in the passages. "
    "Cite every passage you use with its id in square brackets, for example "
    "[course:50:0]. Keep the answer under {words} words, in plain spoken English. "
    "If the passages do not answer the question, reply with exactly NOT_FOUND."
)


def _limit_words(text: str, n: int) -> str:
    if len(text.split()) <= n:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    for s in sentences:
        if len(" ".join([*out, s]).split()) > n:
            break
        out.append(s)
    return " ".join(out) if out else " ".join(text.split()[:n])


def rag_answer(
    question: str,
    kb: KnowledgeBase,
    index: HybridIndex,
    llm: LLM,
    cfg: AppConfig,
    intent: IntentName = "course_info",
    confidence: float = 1.0,
) -> Response:
    """Answer an open question from retrieved passages only.

    Args:
        question: Visitor question (resolved for follow-ups).
        kb: Knowledge base (for handover contacts).
        index: Retrieval index.
        llm: Language model.
        cfg: Thresholds and limits.
        intent: Intent to report.
        confidence: Intent confidence.

    Returns:
        A verified ``text`` answer, or a handover with reason ``retrieval_gate``,
        ``not_found``, ``verify_failed`` or ``llm_unavailable``.
    """
    hits = index.search(question, cfg.top_k)
    if not hits or max(score for _, score in hits) < cfg.retrieval_threshold:
        return handover_response(kb, "retrieval_gate", intent, confidence)
    chunks = [c for c, _ in hits]
    passages = "\n".join(f"[{c.id}] {c.text}" for c in chunks)
    user = f"Passages:\n{passages}\n\nQuestion: {question}"
    try:
        reply = llm.complete(SYSTEM_PROMPT.format(words=cfg.max_speech_words), user).strip()
    except LLMUnavailable:
        return handover_response(kb, "llm_unavailable", intent, confidence)
    if "NOT_FOUND" in reply or not reply:
        return handover_response(kb, "not_found", intent, confidence)
    result = verify(reply, chunks)
    if not result.ok:
        r = handover_response(kb, "verify_failed", intent, confidence)
        r.card.data["verify_reasons"] = result.reasons
        return r
    cited_ids = list(dict.fromkeys(CITATION_RE.findall(reply)))
    cited = [c for c in chunks if c.id in cited_ids]
    speech = _limit_words(strip_citations(reply), cfg.max_speech_words)
    urls = list(dict.fromkeys(c.url for c in cited if c.url))
    return Response(
        speech=speech,
        card=Card(
            kind="text",
            data={
                "answer": speech,
                "passages": [
                    {"id": c.id, "text": c.text[:300], "source": c.source, "url": c.url}
                    for c in cited
                ],
            },
        ),
        links=[Link(label="More information", url=u) for u in urls],
        sources=cited_ids,
        verified=True,
        intent=intent,
        confidence=confidence,
    )
