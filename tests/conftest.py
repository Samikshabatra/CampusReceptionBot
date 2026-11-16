from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from reception.kb.loader import KnowledgeBase, load_kb

IST = ZoneInfo("Asia/Kolkata")


def dt(s: str) -> datetime:
    """Build an Asia/Kolkata datetime from 'YYYY-MM-DD HH:MM'."""
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=IST)


@pytest.fixture(scope="session")
def kb() -> KnowledgeBase:
    return load_kb(Path("knowledge"))


@pytest.fixture(scope="session")
def index(kb: KnowledgeBase):  # type: ignore[no-untyped-def]
    """Retrieval index over the real knowledge base (built once per test run)."""
    from reception.config import load_config
    from reception.rag.index import HybridIndex, build_chunks

    cfg = load_config(Path("configs/app.yaml"))
    return HybridIndex.build(build_chunks(kb), cfg.embedding_model)


@pytest.fixture(scope="session")
def classifier():  # type: ignore[no-untyped-def]
    """Saved model if present, else trained on the train split (seeded)."""
    from reception.config import load_config
    from reception.nlu.intent import IntentClassifier, load_intents

    cfg = load_config(Path("configs/app.yaml"))
    if cfg.intent_model_path.exists():
        return IntentClassifier.load(cfg.intent_model_path)
    rows = [r for r in load_intents(Path("eval/datasets/intents.csv")) if r.split == "train"]
    clf = IntentClassifier(cfg.embedding_model, cfg.seed)
    clf.fit([r.text for r in rows], [r.intent for r in rows])
    return clf
