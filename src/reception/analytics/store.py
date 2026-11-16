"""Anonymised interaction log (SQLite) and the numbers the dashboard shows."""

import csv
import io
import json
import re
import sqlite3
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from reception.types import Response

_PHONE = re.compile(r"\+?\d[\d\s-]{7,}\d")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
FAILURE_REASONS = {
    "room_not_found", "not_in_block", "retrieval_gate", "not_found", "verify_failed",
    "low_confidence", "llm_unavailable", "calendar_expired", "no_hours",
}  # fmt: skip
_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, started_at TEXT, ended_at TEXT, started_by TEXT, ended_by TEXT);
CREATE TABLE IF NOT EXISTS turns(
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, ts TEXT, mode TEXT,
  text_masked TEXT, intent TEXT, confidence REAL, card_kind TEXT, targets_json TEXT,
  sources_json TEXT, verified INTEGER, handover_reason TEXT, latency_json TEXT,
  total_ms REAL, stt_logprob REAL, lang TEXT DEFAULT 'en');
CREATE INDEX IF NOT EXISTS turns_ts ON turns(ts);
"""


def mask_pii(text: str) -> str:
    """Replace phone numbers and emails before anything is stored."""
    return _PHONE.sub("[phone]", _EMAIL.sub("[email]", text))


class AnalyticsStore:
    """Thread-safe SQLite store for sessions and turns."""

    def __init__(self, path: Path) -> None:
        """Open (and create) the database."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(_SCHEMA)
        cols = {row[1] for row in self.db.execute("PRAGMA table_info(turns)")}
        if "lang" not in cols:  # databases created before Hindi/Kannada support
            self.db.execute("ALTER TABLE turns ADD COLUMN lang TEXT DEFAULT 'en'")
        self.lock = threading.Lock()

    def start_session(self, session_id: str, at: datetime, started_by: str) -> None:
        """Record a new visitor session."""
        with self.lock, self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO sessions(id, started_at, started_by) VALUES (?,?,?)",
                (session_id, at.isoformat(), started_by),
            )

    def end_session(self, session_id: str, at: datetime, ended_by: str) -> None:
        """Close a session."""
        with self.lock, self.db:
            self.db.execute(
                "UPDATE sessions SET ended_at=?, ended_by=? WHERE id=? AND ended_at IS NULL",
                (at.isoformat(), ended_by, session_id),
            )

    def log_turn(
        self,
        session_id: str,
        at: datetime,
        mode: str,
        text: str,
        r: Response,
        latency_ms: dict[str, float],
        stt_logprob: float | None,
        lang: str = "en",
    ) -> None:
        """Record one question/answer (text is masked first; Hindi/Kannada stored in English)."""
        targets = r.card.data.get("targets") if r.card.kind == "map" else None
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO turns(session_id, ts, mode, text_masked, intent, confidence, "
                "card_kind, targets_json, sources_json, verified, handover_reason, "
                "latency_json, total_ms, stt_logprob, lang) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session_id, at.isoformat(), mode, mask_pii(text.strip())[:500], r.intent,
                    r.confidence, r.card.kind, json.dumps(targets), json.dumps(r.sources),
                    int(r.verified), r.handover_reason, json.dumps(latency_ms),
                    float(sum(latency_ms.values())), stt_logprob, lang,
                ),
            )  # fmt: skip

    def _rows(self, since: datetime) -> list[sqlite3.Row]:
        self.db.row_factory = sqlite3.Row
        try:
            return list(self.db.execute("SELECT * FROM turns WHERE ts >= ?", (since.isoformat(),)))
        finally:
            self.db.row_factory = None

    def summary(self, since: datetime, top: int = 10) -> dict[str, Any]:
        """Dashboard numbers for turns at or after ``since``.

        Returns:
            Sessions, turns, top queries/intents/locations, failed and handover queries,
            latency (avg/p95), average session length, usage by hour and input mode.
        """
        with self.lock:
            rows = self._rows(since)
            sess = list(
                self.db.execute(
                    "SELECT started_at, ended_at FROM sessions WHERE started_at >= ?",
                    (since.isoformat(),),
                )
            )
        texts = Counter(r["text_masked"].lower() for r in rows if r["text_masked"])
        locations: Counter[str] = Counter()
        for r in rows:
            targets = json.loads(r["targets_json"] or "null")
            if targets:
                locations[targets[0]] += 1
        failed = [
            {
                "text": r["text_masked"],
                "intent": r["intent"],
                "reason": r["handover_reason"] or "clarify",
            }
            for r in rows
            if r["card_kind"] == "clarify"
            and r["intent"] != "greeting"
            or (r["handover_reason"] in FAILURE_REASONS)
        ]
        handovers = [
            {"text": r["text_masked"], "reason": r["handover_reason"]}
            for r in rows
            if r["handover_reason"]
        ]
        totals = [r["total_ms"] for r in rows]
        durations = [
            (datetime.fromisoformat(e) - datetime.fromisoformat(s)).total_seconds()
            for s, e in sess
            if e
        ]
        return {
            "sessions": len(sess),
            "turns": len(rows),
            "top_queries": [{"text": t, "count": c} for t, c in texts.most_common(top)],
            "top_intents": [
                {"intent": i, "count": c}
                for i, c in Counter(r["intent"] for r in rows).most_common(top)
            ],
            "top_locations": [{"place_id": p, "count": c} for p, c in locations.most_common(top)],
            "failed_queries": failed[-50:],
            "handover_queries": handovers[-50:],
            "latency_ms": {
                "avg": float(np.mean(totals)) if totals else 0.0,
                "p95": float(np.percentile(totals, 95)) if totals else 0.0,
            },
            "avg_session_s": float(np.mean(durations)) if durations else 0.0,
            "by_hour": dict(Counter(str(datetime.fromisoformat(r["ts"]).hour) for r in rows)),
            "by_mode": dict(Counter(r["mode"] for r in rows)),
            "by_language": dict(Counter(r["lang"] or "en" for r in rows)),
        }

    def export_csv(self) -> str:
        """All turns as CSV (already anonymised)."""
        cols = ["session_id", "ts", "mode", "text_masked", "intent", "confidence", "card_kind",
                "handover_reason", "verified", "total_ms", "lang"]  # fmt: skip
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        with self.lock:
            w.writerows(self.db.execute(f"SELECT {', '.join(cols)} FROM turns ORDER BY ts"))
        return buf.getvalue()
