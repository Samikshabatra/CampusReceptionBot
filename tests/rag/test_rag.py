import pytest

from reception.config import AppConfig, LLMConfig
from reception.copy import HANDOVER_LINE
from reception.kb.loader import KnowledgeBase
from reception.llm.base import FakeLLM, LLMUnavailable
from reception.llm.ollama import OllamaLLM
from reception.rag.answer import rag_answer
from reception.rag.index import Chunk, HybridIndex, build_chunks
from reception.rag.verify import verify

CH = Chunk(
    id="course:50:0", text="MCA is a 2 year programme. Fee 2,42,000 INR.", source="csv", url=None
)


@pytest.fixture(scope="module")
def cfg() -> AppConfig:
    return AppConfig()


@pytest.fixture(scope="module")
def index(kb: KnowledgeBase, cfg: AppConfig) -> HybridIndex:
    return HybridIndex.build(build_chunks(kb), cfg.embedding_model)


def test_build_chunks(kb: KnowledgeBase) -> None:
    chunks = build_chunks(kb)
    ids = {c.id for c in chunks}
    assert "course:50:facts" in ids and "place:xerox_shop" in ids and "faq:faq_print" in ids
    assert all(len(c.text) <= 800 for c in chunks)
    assert len(ids) == len(chunks)


def test_search_finds_mca(index: HybridIndex) -> None:
    assert index.search("what is the MCA programme about", 5)[0][0].id.startswith("course:50:")


def test_search_scores_unrelated_lower(index: HybridIndex) -> None:
    related = index.search("what is the MCA programme about", 5)[0][1]
    unrelated = max(s for _, s in index.search("who won the cricket match yesterday", 5))
    assert related > unrelated


def test_verify_rejects_unsupported_number() -> None:
    assert not verify("Fees are 3,00,000 [course:50:0]", [CH]).ok


def test_verify_rejects_no_citation() -> None:
    assert not verify("MCA is a 2 year course.", [CH]).ok


def test_verify_rejects_unknown_citation() -> None:
    assert not verify("MCA is a 2 year course [course:99:0].", [CH]).ok


def test_verify_accepts_supported() -> None:
    r = verify("MCA is a 2 year programme costing 2,42,000 [course:50:0].", [CH])
    assert r.ok, r.reasons


def test_verify_rejects_unsupported_email() -> None:
    assert not verify("Email mca@christ.in [course:50:0].", [CH]).ok


def test_gate_skips_llm(kb: KnowledgeBase, index: HybridIndex, cfg: AppConfig) -> None:
    llm = FakeLLM([])
    r = rag_answer("who won the cricket match yesterday", kb, index, llm, cfg)
    assert r.handover_reason == "retrieval_gate" and llm.calls == []


def test_not_found(kb: KnowledgeBase, index: HybridIndex, cfg: AppConfig) -> None:
    r = rag_answer("what is the MCA programme about", kb, index, FakeLLM(["NOT_FOUND"]), cfg)
    assert r.speech.startswith(HANDOVER_LINE) and r.handover_reason == "not_found"


def test_hallucinated_number_handover(
    kb: KnowledgeBase, index: HybridIndex, cfg: AppConfig
) -> None:
    top = index.search("what is the MCA programme about", 1)[0][0].id
    r = rag_answer(
        "what is the MCA programme about", kb, index, FakeLLM([f"MCA has 999 seats [{top}]"]), cfg
    )
    assert r.handover_reason == "verify_failed"


def test_supported_answer(kb: KnowledgeBase, index: HybridIndex, cfg: AppConfig) -> None:
    top = index.search("what is the MCA programme about", 1)[0][0].id
    llm = FakeLLM([f"It is the Master of Computer Applications programme [{top}]."])
    r = rag_answer("what is the MCA programme about", kb, index, llm, cfg)
    assert r.handover_reason is None and "[" not in r.speech
    assert r.sources == [top] and r.card.kind == "text"
    assert "only" in llm.calls[0][0].lower()


def test_llm_unavailable_handover(kb: KnowledgeBase, index: HybridIndex, cfg: AppConfig) -> None:
    class Down:
        def complete(self, system: str, user: str) -> str:
            raise LLMUnavailable("down")

    r = rag_answer("what is the MCA programme about", kb, index, Down(), cfg)
    assert r.handover_reason == "llm_unavailable"


def test_ollama_unavailable() -> None:
    llm = OllamaLLM(LLMConfig(base_url="http://127.0.0.1:9", timeout_s=1.0))
    with pytest.raises(LLMUnavailable):
        llm.complete("system", "user")
