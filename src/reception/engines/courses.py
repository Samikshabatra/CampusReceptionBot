"""Answers about programmes: overview, fees, lists."""

import re

from reception.kb.loader import KnowledgeBase
from reception.kb.models import FEE_CATEGORIES, FEE_CATEGORY_LABELS, Course, FeeCategory, FeeValue
from reception.speech_format import floor_phrase, speak_money
from reception.types import Card, Link, Response

ACADEMIC_YEAR_TAIL = "for academic year 2027, as published."
NO_REG_FEE = "Not listed — please contact Admissions"
_LEVEL_WORDS = {
    "UG": "an undergraduate",
    "PG": "a postgraduate",
    "PhD": "a doctoral",
    "Certificate / Executive": "an executive",
}
_MAX_NAME_WORDS = 12
_SPOKEN_CATEGORY = {
    "karnataka": "Karnataka students",
    "other_states": "students from other Indian states",
    "nri": "NRI students",
    "oci": "OCI students",
    "saarc": "SAARC, Africa, PIO and ASEAN students",
    "foreign": "other foreign nationals",
}


def speech_name(name: str) -> str:
    """Shorten a programme name for speech (drops Honours variants and minors)."""
    s = re.sub(r"/\s*Honours(?: with [Rr]esearch)?", "", name)
    s = re.sub(r"\s*\((?:with )?minor[^)]*\)", "", s, flags=re.IGNORECASE)
    s = s.replace("(One Year PG)", "(one year)")
    s = re.sub(r"\(\s*\)", "", s)
    s = " ".join(s.split())
    if len(s.split()) > _MAX_NAME_WORDS and "(" in s:
        s = s.split("(")[0].strip()
    if len(s.split()) > _MAX_NAME_WORDS:
        s = " ".join(s.split()[:_MAX_NAME_WORDS])
    return s


def _fee_phrase(v: FeeValue) -> str:
    if v.status == "published" and v.amount is not None and v.currency:
        return speak_money(v.amount, v.currency)
    if v.status == "not_applicable":
        return "not applicable"
    if v.status == "not_published":
        return "not published"
    return "listed on screen"


def _fee_card(c: Course) -> Card:
    years = {
        str(y): {FEE_CATEGORY_LABELS[cat]: cells[cat].raw for cat in FEE_CATEGORIES}
        for y, cells in sorted(c.fees.items())
    }
    return Card(
        kind="fees",
        data={
            "course_id": c.id,
            "name": c.name,
            "academic_year": c.academic_year,
            "years": years,
            "deadlines": {str(k): v for k, v in sorted(c.deadlines.items())},
            "registration_fee": c.registration_fee or NO_REG_FEE,
            "url": c.url,
            "verified": c.verified,
        },
    )


def _course_links(c: Course) -> list[Link]:
    return [Link(label=f"Course page: {c.name}", url=c.url)]


def course_fees_response(
    kb: KnowledgeBase,
    course_id: str,
    category: FeeCategory | None,
    year: int | None,
    confidence: float = 1.0,
) -> Response:
    """Spoken fee summary + full fee table on screen.

    Args:
        kb: Knowledge base.
        course_id: Programme id.
        category: Fee category, or None for the Karnataka / other-states default.
        year: Year of study (default 1).
        confidence: Intent confidence to report.

    Returns:
        A ``fees`` card response.
    """
    c = kb.courses[course_id]
    name = speech_name(c.name)
    y = year or 1
    cells = c.fees.get(y)
    if cells is None:
        speech = f"{name} has no year {y} fee listed. The full table is on screen."
    elif all(v.status == "other" for v in cells.values()):
        speech = f"{name} charges fees per course or paper. The details are on screen."
    elif category:
        label = _SPOKEN_CATEGORY[category]
        fee = _fee_phrase(cells[category])
        speech = f"{name}, year {y} fee for {label}: {fee}, {ACADEMIC_YEAR_TAIL}"
    else:
        ka = _fee_phrase(cells["karnataka"])
        other = _fee_phrase(cells["other_states"])
        if ka == other:
            speech = f"{name}, year {y} fee: {ka}, {ACADEMIC_YEAR_TAIL}"
        else:
            speech = (
                f"{name}, year {y} fee: {ka} for Karnataka and {other} for other states, "
                f"{ACADEMIC_YEAR_TAIL}"
            )
    if cells is not None and "not published" in speech:
        speech = speech.replace(ACADEMIC_YEAR_TAIL, "please contact Admissions.")
    return Response(
        speech=speech,
        card=_fee_card(c),
        links=_course_links(c),
        sources=[f"course:{c.id}"],
        verified=c.verified,
        intent="course_fees",
        confidence=confidence,
    )


def _department_sentence(kb: KnowledgeBase, c: Course) -> str:
    hint = c.location_hint
    if hint is None or hint == "not_in_central_block":
        return f"The {c.department} isn't in Central Block."
    ids = kb.groups.get(hint, [hint])
    place = kb.places[ids[0]]
    if place.floor == kb.template.kiosk_floor:
        return f"The {c.department} is on this floor."
    return f"The {c.department} is {floor_phrase(place.floor)}."


def course_info_response(kb: KnowledgeBase, course_id: str, confidence: float = 1.0) -> Response:
    """Short spoken overview; the description goes on screen only."""
    c = kb.courses[course_id]
    name = speech_name(c.name)
    duration = f" of {c.duration}" if c.duration else ""
    speech = f"{name} is {_LEVEL_WORDS[c.level]} programme{duration}. {_department_sentence(kb, c)}"
    return Response(
        speech=speech,
        card=Card(
            kind="course",
            data={
                "course_id": c.id,
                "name": c.name,
                "level": c.level,
                "duration": c.duration,
                "semesters": c.semesters,
                "department": c.department,
                "school": c.school,
                "description": c.description,
                "location_hint": c.location_hint,
                "url": c.url,
                "verified": c.verified,
                "notes": c.notes,
            },
        ),
        links=_course_links(c),
        sources=[f"course:{c.id}"],
        verified=c.verified,
        intent="course_info",
        confidence=confidence,
    )


def course_list_response(
    kb: KnowledgeBase, department: str | None, level: str | None, confidence: float = 1.0
) -> Response:
    """List programmes, optionally filtered by department and level."""
    items = [
        c
        for c in kb.courses.values()
        if (department is None or c.department == department)
        and (level is None or c.level == level)
    ]
    items.sort(key=lambda c: (c.level, c.name))
    level_word = {"UG": " undergraduate", "PG": " postgraduate", "PhD": " doctoral"}.get(
        level or "", ""
    )
    where = f"The {department}" if department else "Central Campus"
    if items:
        speech = f"{where} offers {len(items)}{level_word} programmes. They're listed on screen."
    else:
        speech = "I couldn't find programmes matching that. The reception desk can help."
    return Response(
        speech=speech,
        card=Card(
            kind="course_list",
            data={
                "department": department,
                "level": level,
                "items": [
                    {"id": c.id, "name": c.name, "level": c.level, "duration": c.duration}
                    for c in items
                ],
            },
        ),
        sources=[f"course:{c.id}" for c in items],
        intent="course_list",
        confidence=confidence,
    )
