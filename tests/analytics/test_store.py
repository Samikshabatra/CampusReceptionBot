from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from reception.analytics.store import AnalyticsStore, mask_pii
from reception.types import Card, Response

IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2026, 11, 4, 10, 0, tzinfo=IST)


def resp(intent: str, kind: str = "text", handover: str | None = None, targets=None) -> Response:  # type: ignore[no-untyped-def]
    data = {"targets": targets} if targets else {}
    return Response(
        speech="x",
        card=Card(kind=kind, data=data),
        intent=intent,
        confidence=0.9,  # type: ignore[arg-type]
        handover_reason=handover,
    )


def test_mask_pii() -> None:
    assert (
        mask_pii("call me on +91 98450 12345 or mail a.b@x.com")
        == "call me on [phone] or mail [email]"
    )
    assert mask_pii("room 806") == "room 806"


@pytest.fixture()
def store(tmp_path: Path) -> AnalyticsStore:
    s = AnalyticsStore(tmp_path / "a.db")
    s.start_session("s1", T0, "vision")
    s.log_turn(
        "s1",
        T0,
        "voice",
        "where is the xerox shop",
        resp("navigate", "map", targets=["xerox_shop"]),
        {"stt_ms": 400, "answer_ms": 100},
        -0.3,
    )
    s.log_turn(
        "s1",
        T0 + timedelta(seconds=20),
        "typed",
        "where is room 806",
        resp("navigate", "handover", "room_not_found"),
        {"answer_ms": 50},
        None,
    )
    s.log_turn(
        "s1",
        T0 + timedelta(seconds=40),
        "typed",
        "my number is 9845012345",
        resp("contact"),
        {"answer_ms": 30},
        None,
    )
    s.end_session("s1", T0 + timedelta(seconds=60), "timeout")
    s.start_session("s2", T0 + timedelta(hours=2), "touch")
    s.log_turn(
        "s2",
        T0 + timedelta(hours=2),
        "typed",
        "where is the xerox shop",
        resp("navigate", "map", targets=["xerox_shop"]),
        {"answer_ms": 120},
        None,
    )
    s.log_turn(
        "s2",
        T0 + timedelta(hours=2, seconds=5),
        "typed",
        "blorp",
        resp("repeat", "clarify"),
        {"answer_ms": 10},
        None,
    )
    return s


def test_no_pii_written(store: AnalyticsStore) -> None:
    texts = [r[0] for r in store.db.execute("SELECT text_masked FROM turns")]
    assert "my number is [phone]" in texts and not any("9845012345" in t for t in texts)


def test_summary(store: AnalyticsStore) -> None:
    s = store.summary(T0 - timedelta(days=1))
    assert s["sessions"] == 2 and s["turns"] == 5
    assert s["top_queries"][0] == {"text": "where is the xerox shop", "count": 2}
    assert s["top_locations"][0] == {"place_id": "xerox_shop", "count": 2}
    assert {q["text"] for q in s["failed_queries"]} == {"where is room 806", "blorp"}
    assert s["handover_queries"][0]["reason"] == "room_not_found"
    assert s["latency_ms"]["avg"] == pytest.approx((500 + 50 + 30 + 120 + 10) / 5)
    assert s["avg_session_s"] == pytest.approx(60.0)
    assert s["by_hour"]["10"] == 3 and s["by_mode"]["voice"] == 1


def test_export_csv(store: AnalyticsStore) -> None:
    csv_text = store.export_csv()
    assert csv_text.splitlines()[0].startswith("session_id,ts,mode")
    assert len(csv_text.strip().splitlines()) == 6
