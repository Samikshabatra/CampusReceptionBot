"""FastAPI app: kiosk page, config, and the kiosk WebSocket (text, camera, microphone)."""

import base64
import binascii
import hashlib
import json
import os
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import numpy as np
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from reception.analytics.hook import AnalyticsHook
from reception.analytics.store import AnalyticsStore
from reception.app_factory import build_assistant
from reception.config import AppConfig, SpeechConfig, VisionConfig
from reception.dialogue.router import Assistant
from reception.kb.loader import KnowledgeError
from reception.server.browse import browse_router
from reception.server.session import KioskSession
from reception.speech.stt import Transcriber, Transcript, decode_pcm
from reception.types import Response
from reception.ui.present import present
from reception.vision.approach import ApproachDetector, Box
from reception.vision.detector import FaceDetector

ROOT = Path(__file__).resolve().parents[3]
WEB_DIR = ROOT / "web"


def ui_version() -> str:
    """Short hash of the kiosk page files; open tabs reload when it changes."""
    h = hashlib.sha1()
    for f in sorted((WEB_DIR / "kiosk").glob("*.*")):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


class Detector(Protocol):
    """Anything that finds faces in a JPEG."""

    def detect(self, jpeg: bytes) -> list[Box]:
        """Return face boxes."""
        ...


class STT(Protocol):
    """Anything that transcribes 16 kHz float32 audio."""

    def transcribe(self, audio: np.ndarray) -> Transcript:
        """Return the transcript."""
        ...


class AppState:
    """Live components shared by all connections (swapped on knowledge reload)."""

    assistant: Assistant
    detector: Detector
    transcriber: STT
    hooks: list[Callable[..., None]]
    store: AnalyticsStore


def create_app(
    assistant_factory: Callable[[], Assistant] | None = None,
    detector_factory: Callable[[VisionConfig], Detector] = FaceDetector,
    transcriber_factory: Callable[[SpeechConfig], STT] = Transcriber,
) -> FastAPI:
    """Build the FastAPI app.

    Args:
        assistant_factory: Builds the Assistant at startup (default: configs/app.yaml).
        detector_factory: Face detector from vision config.
        transcriber_factory: Speech-to-text from speech config.

    Returns:
        The app (``app.state.kiosk`` holds the live components).
    """
    state = AppState()
    state.hooks = []

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        state.assistant = (assistant_factory or build_assistant)()
        state.detector = detector_factory(state.assistant.cfg.vision)
        state.transcriber = transcriber_factory(state.assistant.cfg.speech)
        cfg = state.assistant.cfg
        state.store = AnalyticsStore(cfg.analytics.db_path)
        state.hooks.append(AnalyticsHook(state.store, cfg.timezone))
        yield

    app = FastAPI(title="CHRIST Central Block Assistant", lifespan=lifespan)
    app.state.kiosk = state
    version = ui_version()

    @app.middleware("http")
    async def revalidate_page_files(request: Any, call_next: Any) -> Any:
        # The kiosk browser must never run an old copy of the page after an update.
        response = await call_next(request)
        path = request.url.path
        if path in ("/", "/admin") or path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.mount("/static", StaticFiles(directory=WEB_DIR / "kiosk"), name="static")
    app.include_router(browse_router(lambda: state.assistant))

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "kiosk" / "index.html")

    def check_pin(pin: str | None) -> None:
        expected = os.environ.get("RECEPTION_ADMIN_PIN") or state.assistant.cfg.analytics.admin_pin
        if pin != expected:
            raise HTTPException(status_code=401, detail="Enter the admin PIN.")

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        return FileResponse(WEB_DIR / "admin" / "index.html")

    @app.get("/api/admin/summary")
    async def admin_summary(
        days: int = 7, x_admin_pin: str | None = Header(default=None)
    ) -> dict[str, Any]:
        check_pin(x_admin_pin)
        tz = ZoneInfo(state.assistant.cfg.timezone)
        since = datetime.now(tz) - timedelta(days=days)
        return state.store.summary(since)

    @app.get("/api/admin/export.csv")
    async def admin_export(x_admin_pin: str | None = Header(default=None)) -> PlainTextResponse:
        check_pin(x_admin_pin)
        return PlainTextResponse(state.store.export_csv(), media_type="text/csv")

    @app.post("/api/admin/reload")
    async def admin_reload(x_admin_pin: str | None = Header(default=None)) -> JSONResponse:
        check_pin(x_admin_pin)
        try:
            fresh = await run_in_threadpool(assistant_factory or build_assistant)
        except (KnowledgeError, FileNotFoundError) as e:
            return JSONResponse({"ok": False, "errors": str(e)}, status_code=400)
        state.assistant = fresh
        kb = fresh.kb
        return JSONResponse({"ok": True, "places": len(kb.places), "courses": len(kb.courses)})

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        kb = state.assistant.kb
        return {"ok": True, "places": len(kb.places), "courses": len(kb.courses)}

    @app.get("/api/config")
    async def client_config() -> dict[str, Any]:
        cfg = state.assistant.cfg
        return {
            "vision": {"frame_interval_ms": cfg.vision.frame_interval_ms},
            "speech": cfg.speech.model_dump(include={
                "vad_rms_threshold", "silence_ms", "min_speech_ms", "max_utterance_s"}),
            "kiosk": cfg.kiosk.model_dump(include={"banner_s", "idle_timeout_s"}),
            "ui_version": version,
        }  # fmt: skip

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        conn = Connection(ws, state)
        await ws.send_json({"type": "state", "state": "idle"})
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                    kind = msg["type"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    await conn.error("bad message")
                    continue
                await conn.dispatch(kind, msg)
        except WebSocketDisconnect:
            conn.close()

    return app


class Connection:
    """One kiosk browser connection: its session and vision state."""

    def __init__(self, ws: WebSocket, state: AppState) -> None:
        """Bind to the socket and shared components."""
        self.ws = ws
        self.state = state
        cfg: AppConfig = state.assistant.cfg
        self.session = KioskSession(cfg=cfg.kiosk)
        self.approach = ApproachDetector(cfg.vision)
        self.presence = False

    @property
    def assistant(self) -> Assistant:
        """The live assistant."""
        return self.state.assistant

    def _now(self) -> datetime:
        return datetime.now(ZoneInfo(self.assistant.cfg.timezone))

    async def error(self, message: str) -> None:
        """Report a recoverable problem to the client."""
        await self.ws.send_json({"type": "error", "message": message})

    def close(self) -> None:
        """Connection dropped: end the session."""
        if self.session.active:
            self._emit("session_end", session_id=self.session.id, ended_by="disconnect")

    def _emit(self, event: str, **kw: Any) -> None:
        for hook in self.state.hooks:
            hook(event, **kw)

    async def dispatch(self, kind: str, msg: dict[str, Any]) -> None:
        """Route one client message."""
        t = float(msg.get("t", time.monotonic()))
        if kind == "new_session":
            if self.session.active:
                self._emit("session_end", session_id=self.session.id, ended_by="button")
            self.session.reset()
            await self.ws.send_json({"type": "state", "state": "idle"})
        elif kind in ("ask", "option"):
            await self.answer(
                str(msg.get("text", "")), t, mode="tap" if kind == "option" else "typed"
            )
        elif kind == "frame":
            await self.frame(str(msg.get("jpeg", "")), t)
        elif kind == "audio":
            await self.audio(str(msg.get("pcm", "")), t)
        else:
            await self.error(f"unknown type {kind}")

    async def send_response(self, r: Response, extra: dict[str, Any] | None = None) -> None:
        """Present and send a response, then the next state."""
        a = self.assistant
        data = present(a.kb, a.graph, a.cfg, r)
        data["session_id"] = self.session.id
        await self.ws.send_json({"type": "response", "data": data})
        if self.session.ctx.ended:
            self._emit("session_end", session_id=self.session.id, ended_by="bye")
            self.session.reset()
            await self.ws.send_json({"type": "state", "state": "idle"})
        else:
            await self.ws.send_json({"type": "state", "state": "listening"})

    async def answer(self, text: str, t: float, mode: str, stt: Transcript | None = None) -> None:
        """Answer a question from any input mode."""
        was_active = self.session.active
        self.session.on_input(t)
        if not was_active:
            self._emit("session_start", session_id=self.session.id, started_by="touch")
        await self.ws.send_json({"type": "state", "state": "thinking"})
        started = time.perf_counter()
        r = await run_in_threadpool(self.assistant.handle, text, self.session.ctx, self._now())
        ms = (time.perf_counter() - started) * 1000
        self._emit("turn", session_id=self.session.id, text=text, response=r, mode=mode,
                   latency={"answer_ms": ms}, stt=stt)  # fmt: skip
        await self.send_response(r)

    async def frame(self, jpeg_b64: str, t: float) -> None:
        """Process one camera frame (never stored)."""
        try:
            jpeg = base64.b64decode(jpeg_b64, validate=True)
        except (binascii.Error, ValueError):
            await self.error("bad frame")
            return
        boxes = await run_in_threadpool(self.state.detector.detect, jpeg)
        events = self.approach.update(boxes, t)
        if self.approach.present != self.presence:
            self.presence = self.approach.present
            await self.ws.send_json({"type": "presence", "present": self.presence})
        for action in self.session.on_vision(events, self.approach.present, t):
            if action == "greet":
                self._emit("session_start", session_id=self.session.id, started_by="vision")
                await self.send_response(self.assistant.greet(self.session.ctx, self._now()))
            elif action == "banner":
                banner_s = self.assistant.cfg.kiosk.banner_s
                await self.ws.send_json({"type": "banner", "seconds": banner_s})
            elif action == "end":
                self._emit("session_end", session_id=self.session.previous_id, ended_by="timeout")
                await self.ws.send_json({"type": "session_end"})
                await self.ws.send_json({"type": "state", "state": "idle"})

    async def audio(self, pcm_b64: str, t: float) -> None:
        """Transcribe one utterance and answer it."""
        try:
            pcm = decode_pcm(pcm_b64)
        except ValueError as e:
            await self.error(str(e))
            return
        await self.ws.send_json({"type": "state", "state": "thinking"})
        started = time.perf_counter()
        tr = await run_in_threadpool(self.state.transcriber.transcribe, pcm)
        stt_ms = (time.perf_counter() - started) * 1000
        await self.ws.send_json({"type": "transcript", "text": tr.text, "stt_ms": round(stt_ms)})
        if not tr.text:
            await self.ws.send_json({"type": "state", "state": "listening"})
            return
        await self.answer(tr.text, t, mode="voice", stt=tr)
