import wave
from pathlib import Path

import numpy as np

from reception.copy import FACULTY_LINE, OUT_OF_SCOPE
from reception.eval.run import is_refusal, read_wav, synthetic_detection_scenarios
from reception.types import Card, Response


def r(
    speech: str, kind: str = "text", handover: str | None = None, intent: str = "navigate"
) -> Response:
    return Response(
        speech=speech,
        card=Card(kind=kind),
        intent=intent,
        confidence=1.0,  # type: ignore[arg-type]
        handover_reason=handover,
    )


def test_is_refusal() -> None:
    assert is_refusal(r("x", "handover", "room_not_found"))
    assert is_refusal(r("x", "clarify"))
    assert is_refusal(r(OUT_OF_SCOPE, intent="out_of_scope"))
    assert is_refusal(r(FACULTY_LINE, "map", intent="faculty"))
    assert not is_refusal(r("Room 812 is on this floor."))


def test_read_wav(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((np.ones(1600) * 16384).astype("<i2").tobytes())
    audio = read_wav(p)
    assert audio.dtype == np.float32 and len(audio) == 1600 and abs(audio[0] - 0.5) < 1e-3


def test_synthetic_scenarios_are_labelled_and_seeded() -> None:
    a = synthetic_detection_scenarios(n=20, seed=1)
    b = synthetic_detection_scenarios(n=20, seed=1)
    assert [s.label for s in a] == [s.label for s in b]
    assert {s.kind for s in a} <= {"approach", "walk_past", "far", "linger", "off_centre", "group"}
