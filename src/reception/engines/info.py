"""Answers about hours, contacts, faculty and events."""

import re
from datetime import date, datetime, timedelta
from typing import Literal

import networkx as nx

from reception.config import AppConfig
from reception.copy import CALENDAR_EXPIRED, FACULTY_LINE, UNVERIFIED_SUFFIX
from reception.dialogue.handover import contact_items, contact_link, handover_response
from reception.engines.navigation import navigation_response
from reception.engines.timings import CalendarExpired, DayHours, Status, status_at
from reception.kb.loader import KnowledgeBase
from reception.speech_format import (
    floor_phrase,
    place_phrase,
    speak_date,
    speak_phone,
    speak_range,
    speak_time,
    speakable,
)
from reception.types import Card, Link, Response

ContactTopic = Literal["general", "admissions", "library", "all"]
EventQuery = Literal["upcoming", "holidays", "admissions", "open_day"]
_EVENT_WORD_BUDGET = 34
_GROUP_PHRASE = {"offices": "The offices", "services": "That service"}


def _hours_text(h: DayHours) -> str:
    if h.open is None or h.close is None:
        return "closed"
    return f"{speak_time(h.open)} to {speak_time(h.close)}"


def _closed_reason(h: DayHours) -> str:
    if h.reason == "holiday" and h.holiday_name:
        return f" today for {speakable(h.holiday_name)}"
    if h.reason == "third_saturday":
        return " today, as it's the third Saturday"
    if h.reason == "sunday":
        return " on Sundays"
    return ""


def _when(next_open: datetime, at: datetime) -> str:
    t = speak_time(next_open.time())
    if next_open.date() == at.date():
        return f"at {t}"
    if next_open.date() == at.date() + timedelta(days=1):
        return f"tomorrow, {speak_date(next_open.date())}, at {t}"
    return f"on {next_open.strftime('%A')}, {speak_date(next_open.date())}, at {t}"


def _status_sentence(phrase: str, s: Status, at: datetime) -> str:
    if s.is_open:
        text = f"{phrase} is open now. Today's hours are {_hours_text(s.today)}"
        if s.today.lunch and at.time() < s.today.lunch[0]:
            lunch = s.today.lunch
            text += f", with lunch from {speak_time(lunch[0])} to {speak_time(lunch[1])}"
        return text + "."
    if s.on_lunch and s.today.lunch:
        return f"{phrase} is closed for lunch now and reopens at {speak_time(s.today.lunch[1])}."
    text = f"{phrase} is closed now{_closed_reason(s.today)}."
    if s.next_open:
        text += f" It opens {_when(s.next_open, at)}."
    return text


def hours_response(
    kb: KnowledgeBase, place_or_group: str, at: datetime, confidence: float = 1.0
) -> Response:
    """Open/closed now, today's hours and next opening.

    Args:
        kb: Knowledge base.
        place_or_group: Place id or hours group name (``offices``, ``library``).
        at: Current moment (Asia/Kolkata).
        confidence: Intent confidence to report.

    Returns:
        A ``timings`` card response, or a handover when hours are unknown/expired.
    """
    if place_or_group in kb.hours:
        group = kb.hours[place_or_group]
        phrase = (
            place_phrase(kb.places["library"])
            if place_or_group == "library"
            else _GROUP_PHRASE.get(place_or_group, "It")
        )
        name = place_or_group
    else:
        place = kb.places[place_or_group]
        if place.hours_group is None:
            speech = f"I don't have opening hours for {place_phrase(place, capital=False)}."
            return handover_response(kb, "no_hours", "facility_hours", confidence, speech)
        group = kb.hours[place.hours_group]
        phrase = place_phrase(place)
        name = place.name
    try:
        s = status_at(group, at, kb.calendar)
    except CalendarExpired:
        return handover_response(
            kb, "calendar_expired", "facility_hours", confidence, CALENDAR_EXPIRED
        )
    speech = _status_sentence(phrase, s, at)
    if not s.verified:
        speech += UNVERIFIED_SUFFIX
    links = [lk for lk in [library_link(kb)] if lk] if group.name == "library" else []
    return Response(
        speech=speech,
        card=Card(
            kind="timings",
            data={
                "name": name,
                "group": group.name,
                "is_open": s.is_open,
                "on_lunch": s.on_lunch,
                "today": _hours_text(s.today),
                "reason": s.today.reason,
                "holiday": s.today.holiday_name,
                "next_open": s.next_open.isoformat() if s.next_open else None,
                "verified": s.verified,
                "rules": group.model_dump(mode="json"),
            },
        ),
        links=links,
        sources=["hours", "calendar"],
        verified=s.verified,
        intent="facility_hours",
        confidence=confidence,
    )


def college_open_response(kb: KnowledgeBase, at: datetime, confidence: float = 1.0) -> Response:
    """Per-facility answer to "is the college open today?"."""
    parts: list[str] = []
    data: dict[str, object] = {}
    try:
        for label, key in (("Offices are", "offices"), ("The library is", "library")):
            s = status_at(kb.hours[key], at, kb.calendar)
            if s.today.open is None:
                parts.append(f"{label} closed{_closed_reason(s.today)}.")
            else:
                parts.append(f"{label} open today, {_hours_text(s.today)}.")
            data[key] = {"today": _hours_text(s.today), "reason": s.today.reason}
    except CalendarExpired:
        return handover_response(
            kb, "calendar_expired", "college_open", confidence, CALENDAR_EXPIRED
        )
    return Response(
        speech=" ".join(parts),
        card=Card(kind="timings", data={"name": "Central Block", **data}),
        sources=["hours", "calendar"],
        intent="college_open",
        confidence=confidence,
    )


def contact_response(kb: KnowledgeBase, topic: ContactTopic, confidence: float = 1.0) -> Response:
    """Phones/emails/links for a topic, spoken briefly and shown with QR codes."""
    if topic == "general":
        items = contact_items(kb, ("general",))
        first = next(c for c in items if c.kind == "phone")
        speech = (
            f"You can call General and Customer Support on {speak_phone(first.value)}. "
            "All numbers and emails are on screen."
        )
    elif topic == "admissions":
        items = contact_items(kb, ("admissions",))
        first = next(c for c in items if c.kind == "phone")
        speech = (
            f"Call the Admissions Office on {speak_phone(first.value)}, or email them. "
            "Details are on screen."
        )
    elif topic == "library":
        items = contact_items(kb, ("library",))
        speech = "The library website is on screen. Scan the QR code to open it."
    else:
        items = contact_items(kb, ("general", "admissions"))
        speech = "Here are the reception and admissions contacts. Scan a QR code to save one."
    return Response(
        speech=speech,
        card=Card(kind="contacts", data={"topic": topic, "items": [c.model_dump() for c in items]}),
        links=[contact_link(c) for c in items],
        sources=["contacts"],
        intent="contact",
        confidence=confidence,
    )


def faculty_response(
    kb: KnowledgeBase,
    g: nx.Graph,
    cfg: AppConfig,
    department: str | None,
    confidence: float = 1.0,
) -> Response:
    """Fixed faculty answer + KnowledgePro link + route to the Faculty Staff Room."""
    nav = navigation_response(kb, g, cfg, ["faculty_staff_room"], "lift")
    speech = FACULTY_LINE
    target = kb.departments.get(department or "")
    if department and target and target not in ("not_in_central_block", "dept_computer_science"):
        ids = kb.groups.get(target, [target])
        speech += f" The {department} is {floor_phrase(kb.places[ids[0]].floor)}."
    kp = [c for c in kb.contacts if c.id == "knowledgepro"]
    return Response(
        speech=speech,
        card=nav.card,
        links=[contact_link(c) for c in kp],
        sources=["floor_map", "contacts"],
        intent="faculty",
        confidence=confidence,
    )


def _fit(prefix: str, items: list[str], empty: str) -> str:
    if not items:
        return empty
    chosen: list[str] = []
    for it in items:
        candidate = prefix + "; ".join([*chosen, it]) + "."
        if chosen and len(candidate.split()) > _EVENT_WORD_BUDGET:
            break
        chosen.append(it)
    return prefix + "; ".join(chosen) + "."


def events_response(
    kb: KnowledgeBase, today: date, query: EventQuery, confidence: float = 1.0
) -> Response:
    """Upcoming events, holidays, admission interviews or open day."""
    cal = kb.calendar
    if today >= cal.valid_until:
        return handover_response(kb, "calendar_expired", "events", confidence, CALENDAR_EXPIRED)
    rows: list[dict[str, str]] = []
    if query == "holidays":
        hols = [h for h in cal.holidays if h.date >= today][:3]
        rows = [
            {"name": h.name, "when": speak_date(h.date), "start": h.date.isoformat()} for h in hols
        ]
        spoken = [f"{speakable(h.name)} on {speak_date(h.date)}" for h in hols]
        speech = _fit("Upcoming holidays: ", spoken, "No more holidays in this calendar.")
    else:
        kinds = {"upcoming": None, "admissions": "admissions", "open_day": "open_day"}[query]
        evs = [e for e in cal.events if e.end >= today and (kinds is None or e.kind == kinds)]
        evs.sort(key=lambda e: e.start)
        evs = evs[:3]
        rows = [
            {"name": e.name, "when": speak_range(e.start, e.end), "start": e.start.isoformat()}
            for e in evs
        ]
        spoken = [f"{speakable(e.name)} on {speak_range(e.start, e.end)}" for e in evs]
        if query == "open_day" and evs:
            e = evs[0]
            speech = f"{speakable(e.name)} is on {speak_range(e.start, e.end)}, at Central Campus."
        else:
            prefix = {"upcoming": "Coming up: ", "admissions": "Admission interviews: "}.get(
                query, "Coming up: "
            )
            speech = _fit(prefix, spoken, "I don't have any upcoming dates for that.")
    return Response(
        speech=speech,
        card=Card(kind="events", data={"query": query, "items": rows, "note": cal.note}),
        sources=["calendar"],
        intent="events",
        confidence=confidence,
    )


def event_lookup_response(
    kb: KnowledgeBase, today: date, text: str, confidence: float = 1.0
) -> Response | None:
    """Answer "when is <named event>?" if a calendar event name appears in ``text``.

    Args:
        kb: Knowledge base.
        today: Current date.
        text: Normalised question.
        confidence: Intent confidence.

    Returns:
        A one-event answer, or None when no event name matches.
    """
    best = None
    for e in kb.calendar.events:
        words = [w for w in speakable(e.name).lower().replace("'", "").split() if len(w) >= 5]
        words = [w.strip("()-,") for w in words]
        if words and any(re.search(rf"\b{re.escape(w)}", text) for w in words[:2]):
            if best is None or (best.end < today <= e.end):
                best = e
    if best is None:
        return None
    when = speak_range(best.start, best.end)
    past = " That date has passed." if best.end < today else ""
    return Response(
        speech=f"{speakable(best.name)} is on {when}, at Central Campus.{past}",
        card=Card(
            kind="events",
            data={"query": "named", "items": [{"name": best.name, "when": when}], "note": ""},
        ),
        sources=["calendar"],
        intent="events",
        confidence=confidence,
    )


def admissions_response(kb: KnowledgeBase, today: date, confidence: float = 1.0) -> Response:
    """Admissions phone + next interview dates."""
    items = contact_items(kb, ("admissions",))
    phone = next(c for c in items if c.kind == "phone")
    nxt = [e for e in kb.calendar.events if e.kind == "admissions" and e.end >= today]
    speech = f"For admissions, call {speak_phone(phone.value)}."
    if nxt:
        speech += f" The next admission interviews are on {speak_range(nxt[0].start, nxt[0].end)}."
    speech += " Details are on screen."
    return Response(
        speech=speech,
        card=Card(
            kind="contacts",
            data={
                "topic": "admissions",
                "items": [c.model_dump() for c in items],
                "events": [{"name": e.name, "when": speak_range(e.start, e.end)} for e in nxt],
            },
        ),
        links=[contact_link(c) for c in items],
        sources=["contacts", "calendar"],
        intent="admissions",
        confidence=confidence,
    )


_LIBRARY_TOPICS: list[tuple[str, str]] = [
    (r"\b(renew\w*)\b", "renew a book"),
    (r"\b(return\w*|due date)\b", "return a book"),
    (r"\b(issue\w*|borrow\w*|lend\w*|check out|take home)\b", "issue or borrow books"),
    (r"\b(member\w*|card|join|register\w*|sign up)\b", "get library membership"),
    (
        r"\b(e ?journals?|journals?|e ?resources?|databases?|e ?books?|digital|online|"
        r"remote access)\b",
        "access e-resources",
    ),
    (
        r"\b(catalog\w*|search\w*|find (a|the) book|have the book|book available|availability)\b",
        "check if a book is available",
    ),
    (r"\b(fines?|penalty|overdue)\b", "check fines and due dates"),
]


def library_topic(text: str) -> str | None:
    """Short phrase for what the visitor wants from the library, if recognisable."""
    for pattern, phrase in _LIBRARY_TOPICS:
        if re.search(pattern, text):
            return phrase
    return None


def library_link(kb: KnowledgeBase) -> Link | None:
    """The library website link from contacts."""
    site = next((c for c in kb.contacts if c.id == "library_site"), None)
    return Link(label=site.label, url=site.value) if site else None


def library_response(kb: KnowledgeBase, text: str, confidence: float = 1.0) -> Response:
    """Point library questions (issue, renew, membership, e-resources...) to the website.

    Args:
        kb: Knowledge base.
        text: Normalised question.
        confidence: Intent confidence.

    Returns:
        A ``text`` card with the library link and a QR code.
    """
    phrase = library_topic(text)
    if phrase:
        speech = (
            f"To {phrase}, please visit the library website. The link and QR code are on screen."
        )
    else:
        speech = (
            "For details like this, please check the library website. "
            "The link and QR code are on screen."
        )
    link = library_link(kb)
    return Response(
        speech=speech,
        card=Card(
            kind="text",
            data={"text": speech, "library_link": link.url if link else None, "topic": phrase},
        ),
        links=[link] if link else [],
        sources=["contacts"],
        intent="library",
        confidence=confidence,
    )


def admissions_links(kb: KnowledgeBase) -> list[Link]:
    """Admissions phone/email links."""
    return [contact_link(c) for c in contact_items(kb, ("admissions",))]
