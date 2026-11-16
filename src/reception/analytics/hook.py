"""Bridge server events to the analytics store."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from reception.analytics.store import AnalyticsStore


class AnalyticsHook:
    """Called by the server on session_start / turn / session_end."""

    def __init__(self, store: AnalyticsStore, timezone: str) -> None:
        """Log into ``store`` using local time."""
        self.store = store
        self.tz = ZoneInfo(timezone)

    def __call__(self, event: str, **kw: Any) -> None:
        """Record one event; never raises into the conversation."""
        now = datetime.now(self.tz)
        try:
            if event == "session_start":
                self.store.start_session(kw["session_id"], now, kw.get("started_by") or "touch")
            elif event == "turn":
                stt = kw.get("stt")
                self.store.log_turn(
                    kw["session_id"], now, kw["mode"], kw["text"], kw["response"],
                    kw["latency"], stt.avg_logprob if stt else None, kw.get("lang", "en"),
                )  # fmt: skip
            elif event == "session_end":
                self.store.end_session(kw["session_id"], now, kw["ended_by"])
        except Exception as e:  # analytics must never break the kiosk
            print(f"analytics error: {e}")
