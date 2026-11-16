"""Assign dataset splits (once) and train the intent classifier, logging to MLflow."""

import argparse
import csv
import random
import subprocess
from collections import Counter
from pathlib import Path

import mlflow
import yaml
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from reception.config import load_config
from reception.nlu.intent import IntentClassifier, load_intents
from reception.utils.seed import set_seed

SOURCE = Path("eval/datasets/intents_source.yaml")
DATASET = Path("eval/datasets/intents.csv")


def git_commit() -> str:
    """Commit hash if this project is its own git repo, else 'untracked'."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        ).stdout.strip()
        if Path(top).resolve() != Path.cwd().resolve():
            return "untracked"
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "untracked"


def assign_splits(seed: int, val: float, test: float) -> None:
    """Write intents.csv with a stratified split. Refuses to overwrite."""
    if DATASET.exists():
        raise SystemExit(f"{DATASET} exists; splits are fixed. Delete it deliberately to redo.")
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    rng = random.Random(seed)
    rows: list[tuple[str, str, str]] = []
    for intent, texts in source.items():
        items = sorted(set(texts))
        rng.shuffle(items)
        n_val = max(3, round(len(items) * val))
        n_test = max(3, round(len(items) * test))
        for i, t in enumerate(items):
            split = "test" if i < n_test else "val" if i < n_test + n_val else "train"
            rows.append((t, intent, split))
    with open(DATASET, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "intent", "split"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows: {Counter(r[2] for r in rows)}")


def train(config_path: Path) -> None:
    """Train on train split, report on val, save the model, log to MLflow."""
    tcfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg = load_config(Path(tcfg["app_config"]))
    set_seed(cfg.seed)
    rows = load_intents(DATASET)
    train_rows = [r for r in rows if r.split == "train"]
    val_rows = [r for r in rows if r.split == "val"]
    clf = IntentClassifier(cfg.embedding_model, cfg.seed)
    clf.fit([r.text for r in train_rows], [r.intent for r in train_rows])
    y_true = [r.intent for r in val_rows]
    y_pred = [p for p, _ in clf.predict_many([r.text for r in val_rows])]
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro")
    labels = sorted(set(y_true))
    report = classification_report(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    clf.save(cfg.intent_model_path)
    mlflow.set_tracking_uri(tcfg.get("mlflow_uri", "sqlite:///mlflow.db"))
    mlflow.set_experiment("intent")
    with mlflow.start_run():
        mlflow.log_params(
            {
                "embedding_model": cfg.embedding_model,
                "seed": cfg.seed,
                "classifier": "LogisticRegression(C=10, balanced)",
                "n_train": len(train_rows),
                "n_val": len(val_rows),
                "git_commit": git_commit(),
            }
        )
        mlflow.log_metrics({"val_accuracy": acc, "val_macro_f1": f1})
        mlflow.log_text(report, "val_classification_report.txt")
        cm_text = (
            "\t"
            + "\t".join(labels)
            + "\n"
            + "\n".join(
                label + "\t" + "\t".join(str(v) for v in row)
                for label, row in zip(labels, cm, strict=True)
            )
        )
        mlflow.log_text(cm_text, "val_confusion_matrix.tsv")
    errors = [(r.text, r.intent, p) for r, p in zip(val_rows, y_pred, strict=True) if r.intent != p]
    print(f"val accuracy={acc:.3f} macro-F1={f1:.3f} (n={len(val_rows)})")
    for text, gold, pred in errors:
        print(f"  MISS: {text!r}: gold={gold} pred={pred}")
    print(f"saved {cfg.intent_model_path}")


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=Path("configs/intent_train.yaml"))
    ap.add_argument("--assign-splits", action="store_true")
    args = ap.parse_args()
    tcfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if args.assign_splits:
        assign_splits(tcfg["split_seed"], tcfg["val_fraction"], tcfg["test_fraction"])
        return
    train(args.config)


if __name__ == "__main__":
    main()
