import base64
import tempfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from reception.config import load_config
from reception.dialogue.router import Assistant
from reception.engines.navigation import build_graph
from reception.i18n.translate import Lang
from reception.kb.loader import KnowledgeBase
from reception.llm.base import FakeLLM
from reception.server.app import create_app
from reception.speech.stt import Transcript
from reception.vision.approach import Box

HINDI_Q = "पुस्तकालय कहाँ है?"


class NoFace:
    def detect(self, jpeg: bytes) -> list[Box]:
        return []


class HindiSTT:
    def __init__(self) -> None:
        self.languages: list[str] = []

    def transcribe(self, audio: np.ndarray, language: str = "en") -> Transcript:
        self.languages.append(language)
        return Transcript(HINDI_Q, -0.2, 1.0)


class FakeTranslator:
    """Hindi question -> English; English answers -> "[lang] text"."""

    def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        if text == HINDI_Q:
            return "Where is the library?"
        return f"[{tgt}] {text}"


class BrokenTranslator:
    def translate(self, text: str, src: Lang, tgt: Lang) -> str:
        raise RuntimeError("model missing")


def until(ws, kind: str) -> dict:  # type: ignore[no-untyped-def]
    for _ in range(20):
        msg = ws.receive_json()
        if msg["type"] == kind:
            return msg
    raise AssertionError(f"no {kind}")


@pytest.fixture(scope="module")
def assistant(kb: KnowledgeBase, classifier, index) -> Assistant:  # type: ignore[no-untyped-def]
    cfg = load_config(Path("configs/app.yaml"))
    cfg.analytics.db_path = Path(tempfile.mkdtemp()) / "analytics.db"
    return Assistant(kb, cfg, classifier, index, FakeLLM([]), build_graph(kb, cfg))


def make_client(
    assistant: Assistant, translator: object, stt: HindiSTT | None = None
) -> TestClient:
    app = create_app(
        lambda: assistant,
        detector_factory=lambda c: NoFace(),
        transcriber_factory=lambda c: stt or HindiSTT(),
        translator_factory=lambda c: translator,  # type: ignore[arg-type,return-value]
    )
    return TestClient(app)


def test_config_lists_languages(assistant: Assistant) -> None:
    with make_client(assistant, FakeTranslator()) as c:
        assert c.get("/api/config").json()["languages"] == ["en", "hi", "kn"]


def test_choosing_a_language_greets_in_it(assistant: Assistant) -> None:
    with make_client(assistant, FakeTranslator()) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "lang": "kn", "t": 1.0})
        assert until(ws, "language") == {"type": "language", "lang": "kn"}
        r = until(ws, "response")["data"]
        assert r["intent"] == "greeting" and r["speech"].startswith("[kn] ")
        assert r["lang"] == "kn" and len(r["card"]["data"]["option_labels"]) == len(
            r["card"]["data"]["options"]
        )


def test_hindi_question_answered_in_hindi(assistant: Assistant) -> None:
    with make_client(assistant, FakeTranslator()) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "lang": "hi", "t": 1.0})
        until(ws, "response")
        ws.send_json({"type": "ask", "text": HINDI_Q, "t": 2.0})
        r = until(ws, "response")["data"]
        assert r["card"]["data"]["targets"] == ["library"]
        assert r["speech"].startswith("[hi] ") and all(
            s.startswith("[hi] ") for s in r["card"]["data"]["steps"]
        )


def test_spoken_hindi_uses_hindi_speech_model(assistant: Assistant) -> None:
    stt = HindiSTT()
    with make_client(assistant, FakeTranslator(), stt) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "lang": "hi", "t": 1.0})
        until(ws, "response")
        pcm = base64.b64encode(np.zeros(16000, dtype=np.float32).tobytes()).decode()
        ws.send_json({"type": "audio", "pcm": pcm, "t": 2.0})
        assert until(ws, "transcript")["text"] == HINDI_Q  # shown as the visitor said it
        assert until(ws, "response")["data"]["card"]["data"]["targets"] == ["library"]
        assert stt.languages == ["hi"]


def test_unknown_language_falls_back_to_english(assistant: Assistant) -> None:
    with make_client(assistant, FakeTranslator()) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "lang": "fr", "t": 1.0})
        assert until(ws, "language") == {"type": "language", "lang": "en"}
        ws.send_json({"type": "ask", "text": "where is the library", "t": 2.0})
        assert not until(ws, "response")["data"]["speech"].startswith("[")


def test_new_visitor_resets_to_english(assistant: Assistant) -> None:
    with make_client(assistant, FakeTranslator()) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "lang": "hi", "t": 1.0})
        until(ws, "response")
        ws.send_json({"type": "new_session", "t": 2.0})
        until(ws, "state")
        ws.send_json({"type": "ask", "text": "where is the library", "t": 3.0})
        assert not until(ws, "response")["data"]["speech"].startswith("[")


def test_broken_translator_still_answers_in_english(assistant: Assistant) -> None:
    with make_client(assistant, BrokenTranslator()) as c, c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "lang": "hi", "t": 1.0})
        assert until(ws, "response")["data"]["intent"] == "greeting"
        ws.send_json({"type": "ask", "text": "where is the library", "t": 2.0})
        assert until(ws, "response")["data"]["card"]["data"]["targets"] == ["library"]


class FakeVoice:
    async def speak(self, text: str, lang: str) -> bytes:
        from reception.speech.tts import TtsUnavailable

        if lang == "fr":
            raise TtsUnavailable("no voice")
        return f"{lang}:{text}".encode()


def test_tts_endpoint(assistant: Assistant) -> None:
    app = create_app(
        lambda: assistant,
        detector_factory=lambda c: NoFace(),
        transcriber_factory=lambda c: HindiSTT(),
        translator_factory=lambda c: FakeTranslator(),  # type: ignore[arg-type,return-value]
        voice_factory=lambda c: FakeVoice(),  # type: ignore[arg-type,return-value]
    )
    with TestClient(app) as c:
        r = c.get("/api/tts", params={"text": "नमस्ते", "lang": "hi"})
        assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
        assert r.content == "hi:नमस्ते".encode()
        assert c.get("/api/tts", params={"text": "hi", "lang": "fr"}).status_code == 503
        assert c.get("/api/tts", params={"text": " ", "lang": "hi"}).status_code == 400
