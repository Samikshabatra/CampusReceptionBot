from pathlib import Path

import yaml

D = Path("eval/datasets")


def load(name: str):  # type: ignore[no-untyped-def]
    return yaml.safe_load((D / name).read_text(encoding="utf-8"))


def test_qa() -> None:
    items = load("qa.yaml")
    assert len(items) >= 60 and all({"q", "intent", "facts"} <= set(i) for i in items)


def test_tasks() -> None:
    items = load("tasks.yaml")
    assert len(items) >= 20 and all(isinstance(t, str) for i in items for t in i["turns"])


def test_unanswerable_and_retrieval() -> None:
    assert len(load("unanswerable.yaml")) >= 40
    items = load("retrieval.yaml")
    assert len(items) >= 60 and all(i["gold"] for i in items)
