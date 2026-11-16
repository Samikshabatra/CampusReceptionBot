import cv2
import numpy as np

from reception.config import KioskConfig, VisionConfig
from reception.server.session import KioskSession
from reception.vision.approach import VisionEvent
from reception.vision.detector import FaceDetector


def test_blank_frame_has_no_faces() -> None:
    ok, jpg = cv2.imencode(".jpg", np.full((240, 320, 3), 200, np.uint8))
    assert ok and FaceDetector(VisionConfig()).detect(jpg.tobytes()) == []


def test_bad_bytes_do_not_crash() -> None:
    assert FaceDetector(VisionConfig()).detect(b"not a jpeg") == []


def make() -> KioskSession:
    return KioskSession(cfg=KioskConfig())


def test_approach_starts_session_once() -> None:
    s = make()
    assert s.on_vision([VisionEvent("approach", 1)], present=True, t=0.0) == ["greet"]
    assert s.state == "listening" and s.started_by == "vision"
    assert s.on_vision([VisionEvent("approach", 2)], present=True, t=1.0) == ["banner"]


def test_crowd_during_session_shows_banner() -> None:
    s = make()
    s.on_vision([VisionEvent("approach", 1)], present=True, t=0.0)
    assert s.on_vision([VisionEvent("crowd", count=2)], present=True, t=2.0) == ["banner"]


def test_touch_starts_session() -> None:
    s = make()
    s.on_input(t=5.0)
    assert s.state == "listening" and s.started_by == "touch"


def test_ends_only_when_absent_and_idle() -> None:
    s = make()
    s.on_vision([VisionEvent("approach", 1)], present=True, t=0.0)
    s.on_input(t=1.0)
    assert s.on_vision([], present=False, t=12.0) == []  # absent 12 s but input 11 s ago
    assert s.on_vision([], present=False, t=22.0) == ["end"]  # absent and idle long enough
    assert s.state == "idle" and s.ctx.turns == []


def test_present_visitor_keeps_session() -> None:
    s = make()
    s.on_vision([VisionEvent("approach", 1)], present=True, t=0.0)
    assert s.on_vision([], present=True, t=60.0) == []


def test_new_id_after_end() -> None:
    s = make()
    first = s.id
    s.on_vision([VisionEvent("approach", 1)], present=True, t=0.0)
    s.on_vision([], present=False, t=40.0)
    assert s.id != first
