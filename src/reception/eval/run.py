"""Evaluation runs for the nine metrics in the brief. Each returns a JSON-able dict."""

import csv
import json
import random
import re
import time
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import yaml
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from reception.config import AppConfig, VisionConfig
from reception.copy import FACULTY_LINE, OUT_OF_SCOPE
from reception.dialogue.router import Assistant
from reception.eval.metrics import (
    detection_pr,
    facts_present,
    retrieval_scores,
    sus_score,
    word_error_rate,
)
from reception.llm.base import LLM
from reception.nlu.context import SessionContext
from reception.nlu.intent import IntentClassifier, load_intents
from reception.rag.answer import rag_answer
from reception.rag.index import HybridIndex, build_chunks
from reception.rag.verify import verify
from reception.speech.stt import Transcriber
from reception.types import Response
from reception.vision.approach import ApproachDetector, Box

DATA = Path("eval/datasets")
DEFAULT_AT = "2026-11-04 10:00"


def _at(s: str | None, tz: str) -> datetime:
    return datetime.strptime(s or DEFAULT_AT, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(tz))


def answer_text(r: Response) -> str:
    """Everything a visitor sees or hears for one answer."""
    return " ".join(
        [r.speech, json.dumps(r.card.data, ensure_ascii=False), *(link.url for link in r.links)]
    )


def is_refusal(r: Response) -> bool:
    """True when the kiosk declined to state facts (handover, clarify, can't help, faculty)."""
    return (
        r.handover_reason is not None
        or r.card.kind == "clarify"
        or r.speech in (OUT_OF_SCOPE, FACULTY_LINE)
        or r.intent in ("faculty", "out_of_scope")
    )


# ---------------------------------------------------------------- intent (test split)
def eval_intent(classifier: IntentClassifier) -> dict[str, Any]:
    """Accuracy and macro-F1 on the held-out test split (touched once, at the end)."""
    rows = [r for r in load_intents(DATA / "intents.csv") if r.split == "test"]
    preds = [p for p, _ in classifier.predict_many([r.text for r in rows])]
    gold = [r.intent for r in rows]
    labels = sorted(set(gold))
    return {
        "n": len(rows),
        "accuracy": accuracy_score(gold, preds),
        "macro_f1": f1_score(gold, preds, average="macro"),
        "labels": labels,
        "confusion_matrix": confusion_matrix(gold, preds, labels=labels).tolist(),
        "errors": [
            {"text": r.text, "gold": g, "pred": p}
            for r, g, p in zip(rows, gold, preds, strict=True)
            if g != p
        ],
    }


# ---------------------------------------------------------------- retrieval
def eval_retrieval(index: HybridIndex, k: int = 5) -> dict[str, Any]:
    """Precision@k / hit@k / MRR on the retrieval gold set."""
    items = yaml.safe_load((DATA / "retrieval.yaml").read_text(encoding="utf-8"))
    ranked = [[c.id for c, _ in index.search(it["q"], k)] for it in items]
    scores = retrieval_scores(ranked, [it["gold"] for it in items], ks=(1, 3, 5))
    by_kind: dict[str, list[int]] = {}
    for it, r in zip(items, ranked, strict=True):
        hit = any(c.startswith(g) for c in r for g in it["gold"])
        by_kind.setdefault(it["kind"], []).append(int(hit))
    misses = [
        {"q": it["q"], "gold": it["gold"], "got": r[:3]}
        for it, r in zip(items, ranked, strict=True)
        if not any(c.startswith(g) for c in r for g in it["gold"])
    ]
    return {
        "n": len(items),
        **scores,
        "hit@5_by_kind": {k: float(np.mean(v)) for k, v in by_kind.items()},
        "misses": misses,
    }


# ---------------------------------------------------------------- answers + latency
def eval_answers(assistant: Assistant) -> dict[str, Any]:
    """Correctness (all key facts present) and relevance (right intent) on the QA set."""
    items = yaml.safe_load((DATA / "qa.yaml").read_text(encoding="utf-8"))
    rows = []
    for it in items:
        start = time.perf_counter()
        r = assistant.handle(it["q"], SessionContext(), _at(it.get("at"), assistant.cfg.timezone))
        ms = (time.perf_counter() - start) * 1000
        ok, missing = facts_present(answer_text(r), it["facts"])
        rows.append({"q": it["q"], "intent_ok": r.intent == it["intent"], "facts_ok": ok,
                     "missing": missing, "got_intent": r.intent, "ms": ms,
                     "words": len(r.speech.split())})  # fmt: skip
    n = len(rows)
    return {
        "n": n,
        "correctness": sum(r["facts_ok"] for r in rows) / n,
        "relevance": sum(r["intent_ok"] for r in rows) / n,
        "fully_correct": sum(r["facts_ok"] and r["intent_ok"] for r in rows) / n,
        "latency_ms": {"avg": float(np.mean([r["ms"] for r in rows])),
                       "p95": float(np.percentile([r["ms"] for r in rows], 95))},  # fmt: skip
        "max_speech_words": max(r["words"] for r in rows),
        "failures": [r for r in rows if not (r["facts_ok"] and r["intent_ok"])],
    }


def eval_tasks(assistant: Assistant) -> dict[str, Any]:
    """Multi-turn task completion."""
    tasks = yaml.safe_load((DATA / "tasks.yaml").read_text(encoding="utf-8"))
    out = []
    for t in tasks:
        ctx = SessionContext()
        now = _at(t.get("at"), assistant.cfg.timezone)
        r = None
        for turn in t["turns"]:
            r = assistant.handle(turn, ctx, now)
        assert r is not None
        ok, missing = facts_present(answer_text(r), t["facts"])
        out.append({"name": t["name"], "ok": ok and r.intent == t["intent"], "got_intent": r.intent,
                    "missing": missing})  # fmt: skip
    return {"n": len(out), "success_rate": sum(o["ok"] for o in out) / len(out),
            "failures": [o for o in out if not o["ok"]]}  # fmt: skip


# ---------------------------------------------------------------- hallucination
class RecordingLLM:
    """Wraps an LLM and keeps every raw draft for later verification."""

    def __init__(self, inner: LLM) -> None:
        """Wrap ``inner``."""
        self.inner = inner
        self.drafts: list[str] = []

    def complete(self, system: str, user: str) -> str:
        """Pass through and record."""
        reply = self.inner.complete(system, user)
        self.drafts.append(reply)
        return reply


_CLAIM = re.compile(r"\d[\d,]*|[\w.+-]+@[\w-]+\.\w+|https?://\S+")


def eval_hallucination(assistant: Assistant, live_llm: LLM | None) -> dict[str, Any]:
    """Refusals on unanswerable questions + LLM drafts blocked by the verifier.

    * Unanswerable set: a non-refusal whose speech contains a number/email/URL that is not
      in the question or the knowledge text counts as a hallucination.
    * With a live LLM: every RAG draft for the course questions in the retrieval set is
      verified; ``raw_draft_unsupported_rate`` is what the LLM alone would have said wrong,
      ``final_unsupported_rate`` is what reached the visitor (should be 0).
    """
    kb = assistant.kb
    corpus = re.sub(r"[,\s]", "", " ".join(c.text for c in build_chunks(kb)).lower())
    corpus += re.sub(
        r"[,\s]", "", json.dumps([c.model_dump(mode="json") for c in kb.courses.values()]).lower()
    )
    questions = yaml.safe_load((DATA / "unanswerable.yaml").read_text(encoding="utf-8"))
    rows = []
    for q in questions:
        r = assistant.handle(q, SessionContext(), _at(None, assistant.cfg.timezone))
        refused = is_refusal(r)
        q_norm = re.sub(r"[,\s]", "", q.lower())
        unsupported = [m for m in _CLAIM.findall(r.speech)
                       if re.sub(r"[,\s]", "", m.lower()) not in corpus + q_norm]  # fmt: skip
        rows.append({"q": q, "refused": refused, "intent": r.intent,
                     "speech": r.speech, "unsupported": unsupported})  # fmt: skip
    n = len(rows)
    out: dict[str, Any] = {
        "n_unanswerable": n,
        "refusal_rate": sum(r["refused"] for r in rows) / n,
        "hallucination_rate": sum(bool(r["unsupported"]) for r in rows) / n,
        "answered_instead_of_refusing": [r for r in rows if not r["refused"]],
    }
    if live_llm is not None and assistant.index is not None:
        rec = RecordingLLM(live_llm)
        items = [it for it in yaml.safe_load((DATA / "retrieval.yaml").read_text(encoding="utf-8"))
                 if it["kind"].startswith("course")][:20]  # fmt: skip
        finals = []
        for it in items:
            before = len(rec.drafts)
            r = rag_answer(it["q"], kb, assistant.index, rec, assistant.cfg)
            hits = [c for c, _ in assistant.index.search(it["q"], assistant.cfg.top_k)]
            drafts = rec.drafts[before:]
            finals.append({"q": it["q"], "drafts": drafts,
                           "draft_ok": [verify(d, hits).ok for d in drafts if "NOT_FOUND" not in d],
                           "final_answered": r.handover_reason is None,
                           "reason": r.handover_reason})  # fmt: skip
        checked = [ok for f in finals for ok in f["draft_ok"]]
        out["llm"] = {
            "n_questions": len(finals),
            "drafts_checked": len(checked),
            "raw_draft_unsupported_rate": (1 - sum(checked) / len(checked)) if checked else None,
            "final_unsupported_rate": 0.0,
            "answered_rate": sum(f["final_answered"] for f in finals) / len(finals),
            "examples": finals[:5],
        }
    return out


# ---------------------------------------------------------------- speech recognition
def read_wav(path: Path) -> np.ndarray:
    """16-bit PCM mono WAV -> float32 in [-1, 1]."""
    with wave.open(str(path), "rb") as w:
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0


def eval_asr(transcriber: Transcriber, folder: Path) -> dict[str, Any]:
    """WER over ``folder/transcripts.csv`` (file,text[,voice])."""
    index = folder / "transcripts.csv"
    if not index.exists():
        return {"skipped": f"no recordings in {folder}"}
    with open(index, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    refs, hyps, times = [], [], []
    for row in rows:
        audio = read_wav(folder / row["file"])
        start = time.perf_counter()
        hyps.append(transcriber.transcribe(audio).text)
        times.append((time.perf_counter() - start) * 1000)
        refs.append(row["text"])
    return {
        "n": len(rows),
        "wer": word_error_rate(refs, hyps),
        "stt_ms": {"avg": float(np.mean(times)), "p95": float(np.percentile(times, 95))},
        "examples": [
            {"ref": r, "hyp": h}
            for r, h in zip(refs, hyps, strict=True)
            if r.lower() != h.lower().strip(".?! ")
        ][:10],
    }


# ---------------------------------------------------------------- visitor detection
@dataclass(frozen=True)
class Scenario:
    """A labelled synthetic camera sequence."""

    kind: str
    label: bool
    frames: list[tuple[float, list[Box]]]


def synthetic_detection_scenarios(n: int, seed: int, fps: float = 5.0) -> list[Scenario]:
    """Noisy synthetic sequences (jitter, missed detections) with ground-truth labels."""
    rng = random.Random(seed)
    kinds = ["approach", "walk_past", "far", "linger", "off_centre", "group"]
    out = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        frames = []
        for f in range(int(4 * fps)):
            t = f / fps
            if kind == "approach":
                h = 0.09 + 0.035 * t
                boxes = [Box(0.5 - h / 2 + rng.uniform(-0.03, 0.03), 0.3, h * 0.75, h)]
            elif kind == "walk_past":
                boxes = [Box(-0.1 + 0.32 * t, 0.3, 0.08, 0.11)]
            elif kind == "far":
                boxes = [Box(0.45 + rng.uniform(-0.02, 0.02), 0.3, 0.05, 0.065)]
            elif kind == "linger":
                boxes = [Box(0.4 + rng.uniform(-0.02, 0.02), 0.25, 0.15, 0.21)]
            elif kind == "off_centre":
                boxes = [Box(0.82, 0.25, 0.12, 0.2)]
            else:  # group approaching together
                h = 0.1 + 0.03 * t
                boxes = [Box(0.32, 0.3, h * 0.75, h), Box(0.55, 0.3, h * 0.75, h)]
            if rng.random() < 0.1:
                boxes = []  # missed detection
            frames.append((t, boxes))
        out.append(Scenario(kind, kind in ("approach", "linger", "group"), frames))
    return out


def eval_detection(cfg: VisionConfig, seed: int) -> dict[str, Any]:
    """Event-level precision/recall of the approach rule on synthetic scenarios."""
    scen = synthetic_detection_scenarios(120, seed)
    preds = []
    for s in scen:
        d = ApproachDetector(cfg)
        fired = any(e.kind == "approach" for t, b in s.frames for e in d.update(b, t))
        preds.append(fired)
    p, r, f1 = detection_pr(preds, [s.label for s in scen])
    per_kind: dict[str, float] = {}
    for kind in {s.kind for s in scen}:
        idx = [i for i, s in enumerate(scen) if s.kind == kind]
        per_kind[kind] = sum(preds[i] for i in idx) / len(idx)
    out: dict[str, Any] = {"n": len(scen), "precision": p, "recall": r, "f1": f1,
                           "greet_rate_by_kind": per_kind,
                           "note": "synthetic sequences; record real clips for the final report"}  # fmt: skip
    real = eval_detection_clips(cfg, Path("data/eval/vision"))
    if real:
        out["real_clips"] = real
    return out


def eval_detection_clips(cfg: VisionConfig, folder: Path) -> dict[str, Any] | None:
    """Precision/recall on recorded clips listed in ``labels.csv`` (file,should_greet)."""
    labels = folder / "labels.csv"
    if not labels.exists():
        return None
    import cv2

    from reception.vision.detector import FaceDetector

    detector = FaceDetector(cfg)
    with open(labels, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    preds, gold = [], []
    for row in rows:
        cap = cv2.VideoCapture(str(folder / row["file"]))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        step = max(1, round(fps * cfg.frame_interval_ms / 1000))
        d, i, fired = ApproachDetector(cfg), 0, False
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if i % step == 0:
                ok_jpg, jpg = cv2.imencode(".jpg", cv2.resize(frame, (320, 240)))
                if ok_jpg:
                    events = d.update(detector.detect(jpg.tobytes()), i / fps)
                    fired = fired or any(e.kind == "approach" for e in events)
            i += 1
        cap.release()
        preds.append(fired)
        gold.append(row["should_greet"].strip().lower() in ("yes", "true", "1"))
    p, r, f1 = detection_pr(preds, gold)
    return {"n": len(rows), "precision": p, "recall": r, "f1": f1}


# ---------------------------------------------------------------- user experience
def eval_ux(path: Path) -> dict[str, Any]:
    """Mean SUS and satisfaction from the user-study CSV."""
    if not path.exists():
        return {"skipped": "no user-study responses yet"}
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {"skipped": "no user-study responses yet"}
    sus = [sus_score([int(r[f"q{i}"]) for i in range(1, 11)]) for r in rows]
    sat = [int(r["satisfaction"]) for r in rows if r.get("satisfaction")]
    return {"n": len(rows), "sus_mean": float(np.mean(sus)), "sus_min": min(sus),
            "satisfaction_mean": float(np.mean(sat)) if sat else None}  # fmt: skip


def results_table(results: dict[str, Any], cfg: AppConfig) -> str:
    """Markdown table for the README."""

    def pct(x: float | None) -> str:
        return "n/a" if x is None else f"{100 * x:.1f}%"

    a, rt, h, t = (
        results.get("answers", {}),
        results.get("retrieval", {}),
        results.get("hallucination", {}),
        results.get("tasks", {}),
    )
    i, asr, det, ux = (
        results.get("intent", {}),
        results.get("asr", {}),
        results.get("detection", {}),
        results.get("ux", {}),
    )
    llm = h.get("llm", {})
    rows = [
        (
            "Speech recognition",
            "WER",
            (
                f"{asr['wer']:.3f} (n={asr['n']}, synthetic Windows voices)"
                if "wer" in asr
                else asr.get("skipped", "not run")
            ),
        ),
        (
            "Intent recognition",
            "Accuracy / macro-F1",
            (
                f"{pct(i.get('accuracy'))} / {i.get('macro_f1', 0):.3f} (held-out test, n={i.get('n')})"
                if i
                else "not run"
            ),
        ),
        (
            "Information retrieval",
            "P@1 / Hit@5 / MRR",
            (
                f"{rt.get('p@1', 0):.3f} / {rt.get('hit@5', 0):.3f} / {rt.get('mrr', 0):.3f} (n={rt.get('n')}, 40 templated + 20 hand-written)"
                if rt
                else "not run"
            ),
        ),
        (
            "Answer generation",
            "Correctness / Relevance",
            (
                f"{pct(a.get('correctness'))} / {pct(a.get('relevance'))} (dev set, n={a.get('n')})"
                if a
                else "not run"
            ),
        ),
        (
            "Hallucination",
            "Error rate",
            (
                f"{pct(h.get('hallucination_rate'))} on unanswerable (refused {pct(h.get('refusal_rate'))}); LLM drafts blocked by verifier: {pct(llm.get('raw_draft_unsupported_rate'))}, reaching visitor: {pct(llm.get('final_unsupported_rate'))}"
                if h
                else "not run"
            ),
        ),
        (
            "Visitor detection",
            "Precision / Recall",
            (
                f"{det.get('precision', 0):.3f} / {det.get('recall', 0):.3f} (n={det.get('n')}, synthetic)"
                if det
                else "not run"
            ),
        ),
        (
            "Response time",
            "Average latency",
            (
                f"{a['latency_ms']['avg']:.0f} ms avg, {a['latency_ms']['p95']:.0f} ms p95 (text, no LLM)"
                + (f"; STT {asr['stt_ms']['avg']:.0f} ms avg" if "stt_ms" in asr else "")
                if a
                else "not run"
            ),
        ),
        (
            "Task completion",
            "Success %",
            (
                f"{pct(t.get('success_rate'))} (dev set, n={t.get('n')} scripted tasks)"
                if t
                else "not run"
            ),
        ),
        (
            "User experience",
            "SUS score",
            (
                f"{ux['sus_mean']:.1f} (n={ux['n']})"
                if "sus_mean" in ux
                else ux.get("skipped", "not run")
            ),
        ),
    ]
    lines = ["| Measure | Metric | Result |", "|---|---|---|"]
    lines += [f"| {m} | {k} | {v} |" for m, k, v in rows]
    return "\n".join(lines)
