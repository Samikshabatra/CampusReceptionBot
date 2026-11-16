"""Shared response types returned by every answer path."""

from typing import Any, Literal

from pydantic import BaseModel, Field

IntentName = Literal[
    "navigate",
    "facility_hours",
    "college_open",
    "course_info",
    "course_fees",
    "course_list",
    "admissions",
    "contact",
    "faculty",
    "events",
    "library",
    "human",
    "urgent",
    "greeting",
    "thanks_bye",
    "repeat",
    "smalltalk",
    "out_of_scope",
]

CardKind = Literal[
    "map",
    "course",
    "fees",
    "course_list",
    "timings",
    "contacts",
    "events",
    "text",
    "handover",
    "clarify",
]


class Link(BaseModel):
    """A link shown on screen (and as a QR code)."""

    label: str
    url: str


class Card(BaseModel):
    """Display payload for the kiosk screen."""

    kind: CardKind
    data: dict[str, Any] = Field(default_factory=dict)


class Response(BaseModel):
    """One assistant turn: what to say and what to show."""

    speech: str
    card: Card
    links: list[Link] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    verified: bool = True
    intent: IntentName
    confidence: float
    handover_reason: str | None = None
    suggestions: list[str] = Field(default_factory=list)
