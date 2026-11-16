"""Retrieval corpus and hybrid (BM25 + embedding) search."""

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from reception.kb.loader import KnowledgeBase
from reception.nlu.intent import embed
from reception.nlu.normalise import normalise
from reception.speech_format import floor_phrase, speak_range

CHUNK_CHARS = 600
_RRF_K = 60
_MAX_QUERY = 500


@dataclass(frozen=True)
class Chunk:
    """A citable passage of verified text."""

    id: str
    text: str
    source: str
    url: str | None


def _split_sentences(text: str, limit: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    cur = ""
    for s in sentences:
        while len(s) > limit:
            head, s = s[:limit], s[limit:]
            if cur:
                out.append(cur)
                cur = ""
            out.append(head)
        if cur and len(cur) + 1 + len(s) > limit:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def build_chunks(kb: KnowledgeBase) -> list[Chunk]:
    """Turn verified knowledge into citable chunks.

    Args:
        kb: Knowledge base.

    Returns:
        Course fact + description chunks, place, FAQ and event chunks.
    """
    chunks: list[Chunk] = []
    for c in kb.courses.values():
        facts = (
            f"{c.name}. Level: {c.level}. Duration: {c.duration or 'not published'}. "
            f"Semesters: {c.semesters or 'not published'}. Department: {c.department}. "
            f"School: {c.school}. Campus: Bangalore Central Campus. "
            f"Academic year {c.academic_year}."
        )
        chunks.append(Chunk(f"course:{c.id}:facts", facts[:800], "course data", c.url))
        if c.description:
            for i, part in enumerate(_split_sentences(c.description, CHUNK_CHARS)):
                chunks.append(
                    Chunk(f"course:{c.id}:{i}", f"{c.name}: {part}", "course data", c.url)
                )
    for p in kb.places.values():
        if p.category in (
            "room",
            "unknown",
            "stairs",
            "washroom",
            "staff_washroom",
            "water",
            "lockers",
        ):
            continue
        text = f"{p.name} is {floor_phrase(p.floor)} of Central Block."
        if p.department:
            text += f" It is the {p.department}."
        chunks.append(Chunk(f"place:{p.id}", text, "floor map", None))
    for f in kb.faq:
        chunks.append(Chunk(f"faq:{f.id}", f"{f.question} {f.answer}", "faq", None))
    for i, e in enumerate(kb.calendar.events):
        text = f"{e.name}: {speak_range(e.start, e.end)} {e.start.year}, {e.place}."
        chunks.append(Chunk(f"event:{i}", text, "academic calendar", None))
    return chunks


class HybridIndex:
    """BM25 + cosine search fused with reciprocal rank fusion."""

    def __init__(
        self, chunks: list[Chunk], bm25: BM25Okapi, vectors: np.ndarray, model: str
    ) -> None:
        """Use :meth:`build`."""
        self.chunks = chunks
        self.bm25 = bm25
        self.vectors = vectors
        self.model = model

    @classmethod
    def build(cls, chunks: list[Chunk], embedding_model: str) -> "HybridIndex":
        """Index chunks for search."""
        tokens = [normalise(c.text, 10_000).split() for c in chunks]
        bm25 = BM25Okapi(tokens)
        vectors = embed(embedding_model, [c.text for c in chunks])
        return cls(chunks, bm25, vectors, embedding_model)

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        """Top-k chunks by fused rank; the score returned is each chunk's cosine.

        Args:
            query: Visitor question.
            k: How many to return.

        Returns:
            ``(chunk, cosine)`` pairs, best first.
        """
        q_tokens = normalise(query, _MAX_QUERY).split()
        bm = self.bm25.get_scores(q_tokens) if q_tokens else np.zeros(len(self.chunks))
        qv = embed(self.model, [query[:_MAX_QUERY] or "empty"])[0]
        cos = self.vectors @ qv
        rrf = np.zeros(len(self.chunks))
        for scores in (bm, cos):
            order = np.argsort(-scores)
            ranks = np.empty_like(order)
            ranks[order] = np.arange(len(order))
            rrf += 1.0 / (_RRF_K + ranks + 1)
        top = np.argsort(-rrf)[:k]
        return [(self.chunks[i], float(cos[i])) for i in top]
