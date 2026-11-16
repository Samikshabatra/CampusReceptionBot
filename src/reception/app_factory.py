"""Build a ready-to-use Assistant from the config file."""

from pathlib import Path

from reception.config import AppConfig, load_config
from reception.dialogue.router import Assistant
from reception.engines.navigation import build_graph
from reception.kb.loader import load_kb
from reception.llm.base import LLM, FakeLLM
from reception.llm.ollama import OllamaLLM
from reception.nlu.intent import IntentClassifier
from reception.rag.index import HybridIndex, build_chunks


def make_llm(cfg: AppConfig, offline: bool = False) -> LLM:
    """Ollama client, or a fake that always answers NOT_FOUND when offline."""
    if offline or cfg.llm.provider == "fake":
        return FakeLLM([])
    return OllamaLLM(cfg.llm)


def build_assistant(
    config_path: Path = Path("configs/app.yaml"), offline: bool = False
) -> Assistant:
    """Load knowledge, models and index, and wire an Assistant.

    Args:
        config_path: App config YAML.
        offline: Use no LLM (open questions hand over or fall back to facts).

    Returns:
        The assistant.

    Raises:
        FileNotFoundError: The intent model is missing (run scripts/train_intent.py).
    """
    cfg = load_config(config_path)
    kb = load_kb(cfg.knowledge_dir)
    if not cfg.intent_model_path.exists():
        raise FileNotFoundError(
            f"{cfg.intent_model_path} missing - run: uv run python scripts/train_intent.py"
        )
    classifier = IntentClassifier.load(cfg.intent_model_path, cfg.embedding_model)
    index = HybridIndex.build(build_chunks(kb), cfg.embedding_model)
    return Assistant(kb, cfg, classifier, index, make_llm(cfg, offline), build_graph(kb, cfg))
