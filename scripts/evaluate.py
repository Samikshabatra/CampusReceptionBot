"""Run the evaluation suite, save results, log to MLflow and refresh the README table.

Usage:
  uv run python scripts/evaluate.py --config configs/eval.yaml            # everything
  uv run python scripts/evaluate.py --config configs/eval.yaml --only answers tasks
"""

import argparse
import json
import re
from pathlib import Path

import mlflow
import yaml

from reception.app_factory import build_assistant, make_llm
from reception.config import load_config
from reception.eval import run
from reception.llm.base import LLMUnavailable
from reception.speech.stt import Transcriber
from reception.utils.seed import set_seed

ALL = ["intent", "retrieval", "answers", "tasks", "hallucination", "asr", "detection", "ux"]
START, END = "<!-- results:start -->", "<!-- results:end -->"


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=Path("configs/eval.yaml"))
    ap.add_argument("--only", nargs="*", choices=ALL)
    args = ap.parse_args()
    ecfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    cfg = load_config(Path(ecfg["app_config"]))
    set_seed(cfg.seed)
    which = args.only or ALL
    out_dir = Path(ecfg["results_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    assistant = build_assistant(Path(ecfg["app_config"]), offline=True)
    results: dict[str, object] = {}
    for p in out_dir.glob("*.json"):
        results[p.stem] = json.loads(p.read_text(encoding="utf-8"))

    if "intent" in which:
        results["intent"] = run.eval_intent(assistant.classifier)
    if "retrieval" in which:
        assert assistant.index is not None
        results["retrieval"] = run.eval_retrieval(assistant.index)
    if "answers" in which:
        results["answers"] = run.eval_answers(assistant)
    if "tasks" in which:
        results["tasks"] = run.eval_tasks(assistant)
    if "hallucination" in which:
        live = None
        if ecfg.get("use_live_llm", True):
            llm = make_llm(cfg)
            try:
                llm.complete("Reply with OK.", "ping")
                live = llm
            except LLMUnavailable:
                print("LLM not reachable: skipping the live-draft hallucination check.")
        results["hallucination"] = run.eval_hallucination(assistant, live)
    if "asr" in which:
        folder = Path(ecfg["asr_dir"])
        if not (folder / "transcripts.csv").exists():
            folder = Path(ecfg["asr_synthetic_dir"])
        results["asr"] = run.eval_asr(Transcriber(cfg.speech), folder)
        results["asr"]["source"] = str(folder)  # type: ignore[index]
    if "detection" in which:
        results["detection"] = run.eval_detection(cfg.vision, cfg.seed)
    if "ux" in which:
        results["ux"] = run.eval_ux(Path(ecfg["sus_csv"]))

    for name in which:
        (out_dir / f"{name}.json").write_text(
            json.dumps(results[name], indent=1, default=float), encoding="utf-8"
        )
    mlflow.set_tracking_uri(ecfg["mlflow_uri"])
    mlflow.set_experiment("evaluation")
    with mlflow.start_run():
        mlflow.log_params({"embedding_model": cfg.embedding_model, "llm": cfg.llm.model,
                           "stt": cfg.speech.model, "seed": cfg.seed, "evals": ",".join(which)})  # fmt: skip
        for name in which:
            res = results[name]
            if isinstance(res, dict):
                for k, v in res.items():
                    if isinstance(v, int | float) and not isinstance(v, bool):
                        mlflow.log_metric(f"{name}.{k}".replace("@", "_at_"), float(v))
            mlflow.log_dict(res, f"{name}.json")
    table = run.results_table(results, cfg)
    readme = Path("README.md")
    text = readme.read_text(encoding="utf-8")
    if START in text:
        text = re.sub(f"{START}.*?{END}", f"{START}\n{table}\n{END}", text, flags=re.S)
        readme.write_text(text, encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
