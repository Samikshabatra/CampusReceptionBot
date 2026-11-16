from collections import Counter
from pathlib import Path
from typing import get_args

import pytest
from sklearn.metrics import f1_score

from reception.nlu.intent import IntentClassifier, load_intents
from reception.types import IntentName

DATA = Path("eval/datasets/intents.csv")


def test_dataset_shape() -> None:
    rows = load_intents(DATA)
    assert {r.intent for r in rows} == set(get_args(IntentName))
    assert min(Counter(r.intent for r in rows).values()) >= 30
    assert {r.split for r in rows} == {"train", "val", "test"}
    texts = [r.text for r in rows]
    assert len(texts) == len(set(texts)), "duplicate utterances"


def test_split_is_stratified() -> None:
    rows = load_intents(DATA)
    for intent in get_args(IntentName):
        splits = Counter(r.split for r in rows if r.intent == intent)
        assert splits["val"] >= 3 and splits["test"] >= 3, intent


def test_val_macro_f1(classifier: IntentClassifier) -> None:
    val = [r for r in load_intents(DATA) if r.split == "val"]
    pred = [classifier.predict(r.text)[0] for r in val]
    assert f1_score([r.intent for r in val], pred, average="macro") >= 0.85


@pytest.mark.parametrize(
    "text,intent",
    [
        ("where is the library", "navigate"),
        ("library timings", "facility_hours"),
        ("how much is the MCA fee", "course_fees"),
        ("is the college open today", "college_open"),
        ("I want to talk to a person", "human"),
        ("I feel dizzy", "urgent"),
        ("what's the weather", "out_of_scope"),
        ("Where is the zerox shop?", "navigate"),
        ("where is professor sharma", "faculty"),
    ],
)
def test_key_examples(classifier: IntentClassifier, text: str, intent: str) -> None:
    assert classifier.predict(text)[0] == intent


def test_confidence_range(classifier: IntentClassifier) -> None:
    _, conf = classifier.predict("hello")
    assert 0.0 <= conf <= 1.0


def test_save_load_roundtrip(classifier: IntentClassifier, tmp_path: Path) -> None:
    p = tmp_path / "intent.joblib"
    classifier.save(p)
    again = IntentClassifier.load(p)
    assert again.predict("mca fees")[0] == classifier.predict("mca fees")[0]
