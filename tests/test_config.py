from pathlib import Path

from reception.config import load_config


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    p = tmp_path / "app.yaml"
    p.write_text("knowledge_dir: knowledge\nintent_threshold: 0.7\n")
    cfg = load_config(p)
    assert cfg.intent_threshold == 0.7
    assert cfg.timezone == "Asia/Kolkata"
    assert cfg.kiosk_node == "G:kiosk"


def test_repo_config_loads() -> None:
    assert load_config(Path("configs/app.yaml")).llm.provider in ("ollama", "fake")
