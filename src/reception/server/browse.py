"""Read-only endpoints the kiosk screens use for browsing (floors, courses, calendar)."""

import calendar
from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from reception.dialogue.handover import contact_link
from reception.dialogue.router import Assistant
from reception.engines.courses import course_fees_response, course_info_response
from reception.kb.models import FLOORS
from reception.speech_format import floor_name
from reception.ui.floor_svg import render_floor_svg
from reception.ui.present import qr_svg

HIDDEN = {"room", "unknown", "stairs", "washroom", "staff_washroom", "water", "lockers"}


def browse_router(get_assistant: Callable[[], Assistant]) -> APIRouter:
    """Routes for browsing the knowledge base without a conversation turn.

    Args:
        get_assistant: Returns the live assistant (swapped on reload).

    Returns:
        The router.
    """
    r = APIRouter(prefix="/api")

    @r.get("/floor/{floor}.svg")
    def floor_svg(floor: str, highlight: str = "") -> Response:
        kb = get_assistant().kb
        if floor not in kb.floors:
            raise HTTPException(404, "No such floor")
        ids = [h for h in highlight.split(",") if h in kb.places]
        return Response(render_floor_svg(kb, floor, highlight=ids), media_type="image/svg+xml")

    @r.get("/places")
    def places() -> list[dict[str, Any]]:
        kb = get_assistant().kb
        order = {f: i for i, f in enumerate(FLOORS)}
        out = [
            {"id": p.id, "name": p.name, "floor": p.floor, "floor_name": floor_name(p.floor),
             "category": p.category}  # fmt: skip
            for p in kb.places.values()
            if p.category not in HIDDEN and p.primary
        ]
        return sorted(out, key=lambda p: (order[p["floor"]], p["name"]))

    @r.get("/departments")
    def departments() -> list[dict[str, Any]]:
        kb = get_assistant().kb
        out = []
        for dept, target in kb.departments.items():
            count = sum(c.department == dept for c in kb.courses.values())
            floor = None
            if target != "not_in_central_block":
                ids = kb.groups.get(target, [target])
                floor = floor_name(kb.places[ids[0]].floor)
            out.append({"name": dept, "count": count, "floor_name": floor})
        return sorted(out, key=lambda d: (d["floor_name"] is None, d["name"]))

    @r.get("/courses")
    def courses(department: str | None = None, level: str | None = None) -> list[dict[str, Any]]:
        kb = get_assistant().kb
        items = [
            {"id": c.id, "name": c.name, "level": c.level, "duration": c.duration,
             "department": c.department}  # fmt: skip
            for c in kb.courses.values()
            if (department is None or c.department == department)
            and (level is None or c.level == level)
        ]
        return sorted(items, key=lambda c: (c["level"], c["name"]))

    @r.get("/course/{course_id}")
    def course(course_id: str) -> dict[str, Any]:
        kb = get_assistant().kb
        if course_id not in kb.courses:
            raise HTTPException(404, "No such programme")
        info = course_info_response(kb, course_id)
        fees = course_fees_response(kb, course_id, None, None)
        return {
            "course": info.card.data,
            "fees": fees.card.data,
            "speech": info.speech,
            "qr": [{"label": lk.label, "url": lk.url, "svg": qr_svg(lk.url)} for lk in info.links],
        }

    @r.get("/contacts")
    def contacts() -> list[dict[str, Any]]:
        out = []
        for c in get_assistant().kb.contacts:
            href = contact_link(c).url
            out.append({**c.model_dump(), "href": href, "qr": qr_svg(href)})
        return out

    @r.get("/calendar")
    def month(year: int, month: int) -> dict[str, Any]:
        cal = get_assistant().kb.calendar
        if not 1 <= month <= 12:
            raise HTTPException(400, "month must be 1-12")
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        events = [
            {"name": e.name, "start": e.start.isoformat(), "end": e.end.isoformat(), "kind": e.kind}
            for e in cal.events
            if e.start <= last and e.end >= first
        ]
        holidays = [
            {"date": h.date.isoformat(), "name": h.name}
            for h in cal.holidays
            if first <= h.date <= last
        ]
        return {
            "month_name": first.strftime("%B %Y"),
            "first_weekday": first.weekday(),
            "days": last.day,
            "events": events,
            "holidays": holidays,
            "valid": cal.valid_from <= first < cal.valid_until,
        }

    return r
