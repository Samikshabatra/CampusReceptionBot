"""One kiosk conversation and its lifecycle (greet, listen, end)."""

import uuid
from dataclasses import dataclass, field
from typing import Literal

from reception.config import KioskConfig
from reception.nlu.context import SessionContext
from reception.vision.approach import VisionEvent

State = Literal["idle", "listening", "thinking", "handover"]
Action = Literal["greet", "banner", "end"]


@dataclass
class KioskSession:
    """Conversation state for the visitor currently at the kiosk."""

    cfg: KioskConfig = field(default_factory=KioskConfig)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ctx: SessionContext = field(default_factory=SessionContext)
    state: State = "idle"
    started_by: str | None = None
    started_at: float | None = None
    last_input: float = 0.0
    last_seen: float = 0.0
    previous_id: str | None = None
    lang: str = "en"  # conversation language chosen by the visitor

    @property
    def active(self) -> bool:
        """True while a visitor's session is running."""
        return self.state != "idle"

    def _start(self, t: float, by: str) -> None:
        self.state = "listening"
        self.started_by = by
        self.started_at = t
        self.last_input = t
        self.last_seen = t

    def reset(self) -> None:
        """Forget everything about the previous visitor."""
        self.previous_id = self.id
        self.id = uuid.uuid4().hex[:12]
        self.ctx = SessionContext()
        self.lang = "en"
        self.state = "idle"
        self.started_by = None
        self.started_at = None

    def on_input(self, t: float) -> None:
        """A typed/tapped/spoken question arrived."""
        if not self.active:
            self._start(t, "touch")
        self.last_input = t

    def on_vision(self, events: list[VisionEvent], present: bool, t: float) -> list[Action]:
        """React to one processed camera frame.

        Args:
            events: Events from the approach detector.
            present: Whether anyone is in front of the kiosk now.
            t: Frame time (seconds, same clock as ``on_input``).

        Returns:
            Actions for the server: ``greet`` a new visitor, show the ``banner`` for a second
            person, or ``end`` the session (context already wiped).
        """
        actions: list[Action] = []
        if present:
            self.last_seen = t
        for e in events:
            if e.kind == "approach" and not self.active:
                self._start(t, "vision")
                actions.append("greet")
            elif e.kind == "approach" or (e.kind == "crowd" and self.active):
                actions.append("banner")
        if self.active and not present:
            absent = t - self.last_seen >= self.cfg.absent_timeout_s
            idle = t - self.last_input >= self.cfg.idle_timeout_s
            if absent and idle:
                self.reset()
                actions.append("end")
        return list(dict.fromkeys(actions))
