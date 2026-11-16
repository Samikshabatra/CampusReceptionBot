"""Intent classifier: sentence embeddings + logistic regression."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from reception.nlu.normalise import normalise
from reception.types import IntentName

Split = Literal["train", "val", "test"]
_MAX_CHARS = 500
_EMBEDDERS: dict[str, Any] = {}


@dataclass(frozen=True)
class IntentRow:
    """One labelled utterance."""

    text: str
    intent: IntentName
    split: Split


def load_intents(path: Path) -> list[IntentRow]:
    """Read ``text,intent,split`` rows.

    Args:
        path: CSV file.

    Returns:
        Labelled rows.
    """
    with open(path, encoding="utf-8", newline="") as f:
        return [
            IntentRow(r["text"], r["intent"], r["split"])  # type: ignore[arg-type]
            for r in csv.DictReader(f)
        ]


def get_embedder(model_name: str) -> Any:
    """Shared fastembed model (loaded once per process)."""
    if model_name not in _EMBEDDERS:
        from fastembed import TextEmbedding

        _EMBEDDERS[model_name] = TextEmbedding(model_name=model_name)
    return _EMBEDDERS[model_name]


def embed(model_name: str, texts: list[str]) -> np.ndarray:
    """L2-normalised embeddings for texts."""
    vecs = np.array(list(get_embedder(model_name).embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-9)


class IntentClassifier:
    """Predicts one of the IntentName labels with a confidence."""

    def __init__(self, embedding_model: str, seed: int = 42) -> None:
        """Create an untrained classifier.

        Args:
            embedding_model: fastembed model name.
            seed: Random seed for the classifier.
        """
        self.embedding_model = embedding_model
        self.seed = seed
        self.clf = LogisticRegression(
            max_iter=2000, class_weight="balanced", C=10.0, random_state=seed
        )

    def _features(self, texts: list[str]) -> np.ndarray:
        return embed(self.embedding_model, [normalise(t, _MAX_CHARS) or "empty" for t in texts])

    def fit(self, texts: list[str], labels: list[IntentName]) -> None:
        """Train on labelled texts."""
        self.clf.fit(self._features(texts), labels)

    def predict(self, text: str) -> tuple[IntentName, float]:
        """Most likely intent and its probability."""
        proba = self.clf.predict_proba(self._features([text]))[0]
        i = int(np.argmax(proba))
        return self.clf.classes_[i], float(proba[i])

    def predict_many(self, texts: list[str]) -> list[tuple[IntentName, float]]:
        """Batch version of :meth:`predict`."""
        probas = self.clf.predict_proba(self._features(texts))
        idx = probas.argmax(axis=1)
        return [(self.clf.classes_[i], float(p[i])) for i, p in zip(idx, probas, strict=True)]

    def save(self, path: Path) -> None:
        """Persist to a joblib file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"clf": self.clf, "embedding_model": self.embedding_model, "seed": self.seed}, path
        )

    @classmethod
    def load(cls, path: Path, embedding_model: str | None = None) -> "IntentClassifier":
        """Load a classifier saved with :meth:`save`."""
        data = joblib.load(path)
        obj = cls(embedding_model or data["embedding_model"], data["seed"])
        obj.clf = data["clf"]
        return obj
