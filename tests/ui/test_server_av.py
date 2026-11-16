import base64
import tempfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from reception.config import load_config
from reception.dialogue.router import Assistant
from reception.engines.navigation import build_graph
from reception.kb.loader import KnowledgeBase
from reception.llm.base import FakeLLM
from reception.server.app import create_app
from reception.speech.stt import Transcript
from reception.vision.approach import Box


class NearFace:
    def detect(self, jpeg: bytes) -> list[Box]:
        return [] if jpeg == b"empty" else [Box(0.42, 0.25, 0.16, 0.22)]


class FixedSTT:
    def __init__(self, text: str) -> None:
        self.text = text

    def transcribe(self, audio: np.ndarray) -> Transcript:
        return Transcript(self.text, -0.2, len(audio) / 16000)


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def until(ws, kind: str) -> dict:  # type: ignore[no-untyped-def]
    for _ in range(20):
        msg = ws.receive_json()
        if msg["type"] == kind:
            return msg
    raise AssertionError(f"no {kind}")


@pytest.fixture(scope="module")
def client(kb: KnowledgeBase, classifier, index):  # type: ignore[no-untyped-def]
    cfg = load_config(Path("configs/app.yaml"))
    cfg.analytics.db_path = Path(tempfile.mkdtemp()) / "analytics.db"
    assistant = Assistant(kb, cfg, classifier, index, FakeLLM([]), build_graph(kb, cfg))
    app = create_app(
        lambda: assistant,
        detector_factory=lambda c: NearFace(),
        transcriber_factory=lambda c: FixedSTT("where is the library"),
    )
    with TestClient(app) as c:
        yield c


def test_config_endpoint(client: TestClient) -> None:
    body = client.get("/api/config").json()
    assert body["vision"]["frame_interval_ms"] == 200 and "silence_ms" in body["speech"]


def test_approach_greets(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for i in range(10):
            ws.send_json({"type": "frame", "jpeg": b64(b"face"), "t": i * 0.2})
        msg = until(ws, "response")
        assert msg["data"]["intent"] == "greeting" and msg["data"]["card"]["kind"] == "clarify"


def test_empty_frames_never_greet(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for i in range(10):
            ws.send_json({"type": "frame", "jpeg": b64(b"empty"), "t": i * 0.2})
        ws.send_json({"type": "ask", "text": "hello", "t": 3.0})
        assert until(ws, "response")["data"]["intent"] == "greeting"


def test_audio_transcribed_and_answered(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        pcm = np.zeros(16000, dtype=np.float32).tobytes()
        ws.send_json({"type": "audio", "pcm": b64(pcm), "t": 1.0})
        assert until(ws, "transcript")["text"] == "where is the library"
        assert until(ws, "response")["data"]["card"]["data"]["targets"] == ["library"]


def test_bad_audio_reports_error(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "audio", "pcm": "%%%", "t": 1.0})
        assert until(ws, "error")["type"] == "error"
        ws.send_json({"type": "ask", "text": "hello", "t": 2.0})
        assert until(ws, "response")["data"]["intent"] == "greeting"


def test_session_ends_after_absence(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for i in range(10):
            ws.send_json({"type": "frame", "jpeg": b64(b"face"), "t": i * 0.2})
        until(ws, "response")
        ws.send_json({"type": "frame", "jpeg": b64(b"empty"), "t": 60.0})
        assert until(ws, "session_end")["type"] == "session_end"


def test_presence_sent_before_greeting(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "frame", "jpeg": b64(b"face"), "t": 0.0})
        assert until(ws, "presence") == {"type": "presence", "present": True}
        for i in range(1, 10):
            ws.send_json({"type": "frame", "jpeg": b64(b"face"), "t": i * 0.2})
        assert until(ws, "response")["data"]["intent"] == "greeting"
        ws.send_json({"type": "frame", "jpeg": b64(b"empty"), "t": 5.0})
        assert until(ws, "presence") == {"type": "presence", "present": False}


def test_config_has_ui_version(client: TestClient) -> None:
    v1 = client.get("/api/config").json()["ui_version"]
    v2 = client.get("/api/config").json()["ui_version"]
    assert isinstance(v1, str) and len(v1) == 12 and v1 == v2
