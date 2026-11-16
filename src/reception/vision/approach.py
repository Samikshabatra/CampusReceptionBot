"""Decide when a person is approaching the kiosk (not just walking past)."""

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from reception.config import VisionConfig


@dataclass(frozen=True)
class Box:
    """A detection box, normalised to the frame (0-1)."""

    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        """Horizontal centre."""
        return self.x + self.w / 2


def iou(a: Box, b: Box) -> float:
    """Intersection over union of two boxes."""
    ix = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    inter = ix * iy
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


@dataclass
class Track:
    """One person followed across frames."""

    id: int
    history: deque[tuple[float, Box]] = field(default_factory=lambda: deque(maxlen=60))
    greeted: bool = False

    @property
    def last(self) -> tuple[float, Box]:
        """Most recent (time, box)."""
        return self.history[-1]


@dataclass(frozen=True)
class VisionEvent:
    """Something the session should react to."""

    kind: Literal["approach", "left", "crowd"]
    track_id: int = -1
    count: int = 0


class ApproachDetector:
    """Tracks faces and emits approach / left / crowd events."""

    def __init__(self, cfg: VisionConfig) -> None:
        """Create a detector with thresholds from config."""
        self.cfg = cfg
        self.tracks: dict[int, Track] = {}
        self._next_id = 1
        self._last_greet = -1e9
        self._last_crowd = 0

    @property
    def present(self) -> bool:
        """True while anyone big enough is being tracked."""
        return any(t.last[1].h >= self.cfg.min_face for t in self.tracks.values())

    def _match(self, boxes: list[Box], t: float) -> None:
        unmatched = list(boxes)
        for track in sorted(self.tracks.values(), key=lambda tr: -tr.last[1].h):
            best = max(unmatched, key=lambda b: iou(track.last[1], b), default=None)
            if best is not None and iou(track.last[1], best) >= self.cfg.iou_match:
                track.history.append((t, best))
                unmatched.remove(best)
        for b in unmatched:
            tr = Track(self._next_id)
            tr.history.append((t, b))
            self.tracks[tr.id] = tr
            self._next_id += 1

    def _is_approaching(self, track: Track, t: float) -> bool:
        c = self.cfg
        window = [(ts, b) for ts, b in track.history if t - ts <= c.window_s]
        if not window:
            return False
        first_t, first = window[0]
        _, last = window[-1]
        span = t - track.history[0][0]
        if span < c.dwell_s or last.h < c.min_face:
            return False
        if abs(last.cx - 0.5) > c.center_tolerance:
            return False
        if abs(last.cx - first.cx) > c.max_drift:
            return False
        if not c.require_approach:
            return True  # a centred face held for dwell_s is enough
        grew = first.h > 0 and last.h / first.h >= c.growth_ratio
        return grew or last.h >= c.near_height

    def update(self, boxes: list[Box], t: float) -> list[VisionEvent]:
        """Feed one frame's detections.

        Args:
            boxes: Face boxes in this frame.
            t: Frame time in seconds.

        Returns:
            Events triggered by this frame.
        """
        events: list[VisionEvent] = []
        self._match(boxes, t)
        for tid, track in list(self.tracks.items()):
            if t - track.last[0] > self.cfg.max_age_s:
                if track.greeted:
                    events.append(VisionEvent("left", tid))
                del self.tracks[tid]
        for track in self.tracks.values():
            if track.greeted or track.last[0] != t:
                continue
            if self._is_approaching(track, t) and t - self._last_greet >= self.cfg.cooldown_s:
                track.greeted = True
                self._last_greet = t
                events.append(VisionEvent("approach", track.id))
        n = sum(1 for tr in self.tracks.values() if tr.last[1].h >= self.cfg.min_face)
        if n >= 2 and n != self._last_crowd:
            events.append(VisionEvent("crowd", count=n))
        self._last_crowd = n
        return events
