"""Per-visitor conversation memory for follow-up questions."""

import re
from dataclasses import dataclass, field

from reception.kb.models import FeeCategory
from reception.nlu.entities import Entities
from reception.types import IntentName, Response

_MARKERS = re.compile(r"\b(there|it|its|that|this|same|them|they|those)\b")
_ELLIPSIS = re.compile(r"^(and|what about|how about|for|also)\b")
_COURSE_INTENTS = {"course_fees", "course_info", "course_list"}


@dataclass
class SessionContext:
    """What the assistant remembers during one visitor's session."""

    turns: list[tuple[str, Response]] = field(default_factory=list)
    last_place_ids: list[str] = field(default_factory=list)
    last_course_ids: list[str] = field(default_factory=list)
    last_category: FeeCategory | None = None
    last_department: str | None = None
    last_intent: IntentName | None = None
    misunderstandings: int = 0
    ended: bool = False

    @staticmethod
    def is_elliptical(text: str) -> bool:
        """``"and for nri"`` / ``"what about oci"``: a follow-up that reuses the last intent."""
        return bool(_ELLIPSIS.match(text))

    @property
    def last_response(self) -> Response | None:
        """The most recent assistant response, if any."""
        return self.turns[-1][1] if self.turns else None


def resolve(text: str, ents: Entities, ctx: SessionContext) -> Entities:
    """Fill missing entities from the session when the text refers back.

    Args:
        text: Normalised text.
        ents: Entities extracted from this utterance.
        ctx: Session context.

    Returns:
        A copy of ``ents`` with place/course/department filled from context when the text
        contains a reference word (it, there, that...) or starts elliptically (and..., what
        about...). New values in this utterance always win.
    """
    if not (_MARKERS.search(text) or SessionContext.is_elliptical(text)):
        return ents
    e = ents.model_copy(deep=True)
    course_first = ctx.last_intent in _COURSE_INTENTS
    fill_order = ("course", "place") if course_first else ("place", "course")
    for slot in fill_order:
        if e.place_ids or e.room or e.course_ids:
            break
        if slot == "place" and ctx.last_place_ids:
            e.place_ids = list(ctx.last_place_ids)
        elif slot == "course" and ctx.last_course_ids:
            e.course_ids = list(ctx.last_course_ids)
    if e.department is None and ctx.last_department and not e.place_ids:
        e.department = ctx.last_department
    return e
