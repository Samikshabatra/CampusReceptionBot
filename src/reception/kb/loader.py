"""Load and validate every knowledge file into one KnowledgeBase."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from reception.kb.courses_build import read_courses
from reception.kb.layout import GENERIC_TOKENS, expand_layout
from reception.kb.models import (
    FLOOR_ORDER,
    FLOORS,
    CalendarData,
    Contact,
    Course,
    FaqEntry,
    FloorLayout,
    FloorTemplate,
    HoursGroup,
    Place,
)


class KnowledgeError(Exception):
    """Raised with every problem found while loading the knowledge base."""


@dataclass
class KnowledgeBase:
    """All verified facts the assistant may state."""

    places: dict[str, Place]
    floors: dict[str, FloorLayout]
    template: FloorTemplate
    courses: dict[str, Course]
    course_aliases: dict[str, list[str]]
    departments: dict[str, str]
    hours: dict[str, HoursGroup]
    calendar: CalendarData
    contacts: list[Contact]
    faq: list[FaqEntry]
    groups: dict[str, list[str]] = field(default_factory=dict)


def _read_yaml(path: Path, errors: list[str], expect: type = dict) -> Any:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{path.name}: file missing")
        return None
    except yaml.YAMLError as e:
        errors.append(f"{path.name}: invalid YAML ({e.__class__.__name__})")
        return None
    if not isinstance(data, expect):
        errors.append(f"{path.name}: expected a {expect.__name__}, got {type(data).__name__}")
        return None
    return data


def _auto_place(pid: str, floor: str) -> Place | None:
    if pid.startswith("room_"):
        num = pid[5:].upper()
        return Place(
            id=pid,
            name=f"Room {num}",
            article=False,
            category="room",
            floor=floor,  # type: ignore[arg-type]
            room_number=num,
        )
    parts = pid.split("_")
    if len(parts) >= 3 and parts[0] == floor:
        token = "_".join(parts[1:-1])
        if token in GENERIC_TOKENS:
            name, category = GENERIC_TOKENS[token]
            return Place(
                id=pid,
                name=name,
                category=category,
                floor=floor,  # type: ignore[arg-type]
                primary=category != "unknown",
            )
    return None


def load_kb(root: Path) -> KnowledgeBase:
    """Load every knowledge file under ``root``.

    Args:
        root: The ``knowledge/`` directory.

    Returns:
        The validated knowledge base.

    Raises:
        KnowledgeError: Listing every problem found, not just the first.
    """
    root = Path(root)
    errors: list[str] = []

    named_raw = _read_yaml(root / "places.yaml", errors, list) or []
    named: dict[str, Place] = {}
    for item in named_raw:
        try:
            p = Place.model_validate(item)
            if p.id in named:
                errors.append(f"places.yaml: duplicate id {p.id}")
            named[p.id] = p
        except ValidationError as e:
            errors.append(f"places.yaml: {item.get('id', '?')}: {e.errors()[0]['msg']}")

    places: dict[str, Place] = {}
    floors: dict[str, FloorLayout] = {}
    for floor in FLOORS:
        raw = _read_yaml(root / "floors" / f"{floor}.yaml", errors)
        if raw is None:
            continue
        cell_ids: list[str] = []
        for pid, rect in expand_layout(raw):
            cell_ids.append(pid)
            if pid in named:
                p = named[pid]
                if p.floor != floor:
                    errors.append(f"floors/{floor}.yaml: {pid} is declared on floor {p.floor}")
                places[pid] = p.model_copy(update={"rect": rect})
                continue
            auto = _auto_place(pid, floor)
            if auto is None:
                errors.append(f"floors/{floor}.yaml: unknown place id '{pid}'")
                continue
            places[pid] = auto.model_copy(update={"rect": rect})
        floors[floor] = FloorLayout(
            floor=floor,  # type: ignore[arg-type]
            title=str(raw.get("title", "")),
            seating=bool(raw.get("seating", False)),
            cell_ids=cell_ids,
        )
    for pid, p in named.items():
        if pid in places:
            continue
        if p.whole_floor:
            places[pid] = p
        else:
            errors.append(f"places.yaml: {pid} is not placed on any floor layout")

    groups: dict[str, list[str]] = {}
    for p in places.values():
        if p.group:
            groups.setdefault(p.group, []).append(p.id)
    for ids in groups.values():
        ids.sort(key=lambda i: (not places[i].primary, FLOOR_ORDER[places[i].floor], i))

    template_raw = _read_yaml(root / "floor_template.yaml", errors)
    template = None
    if template_raw is not None:
        try:
            template = FloorTemplate.model_validate(template_raw)
        except ValidationError as e:
            errors.append(f"floor_template.yaml: {e.errors()[0]['msg']}")

    courses: dict[str, Course] = {}
    try:
        courses = {c.id: c for c in read_courses(root / "courses.json")}
    except FileNotFoundError:
        errors.append("courses.json: file missing (run scripts/build_kb.py)")

    course_aliases = {
        str(k): [str(a).lower() for a in v]
        for k, v in (_read_yaml(root / "course_aliases.yaml", errors) or {}).items()
    }
    for cid in course_aliases:
        if courses and cid not in courses:
            errors.append(f"course_aliases.yaml: unknown programme id {cid}")
    departments = {
        str(k): str(v) for k, v in (_read_yaml(root / "departments.yaml", errors) or {}).items()
    }
    for dept, target in departments.items():
        if target != "not_in_central_block" and target not in places and target not in groups:
            errors.append(f"departments.yaml: {dept} -> unknown place/group '{target}'")

    hours: dict[str, HoursGroup] = {}
    for name, item in (_read_yaml(root / "hours.yaml", errors) or {}).items():
        try:
            hours[name] = HoursGroup.model_validate({"name": name, **item})
        except (ValidationError, TypeError) as e:
            errors.append(f"hours.yaml: {name}: {e}")
    for p in places.values():
        if p.hours_group and hours and p.hours_group not in hours:
            errors.append(f"places.yaml: {p.id} has unknown hours_group {p.hours_group}")

    calendar = None
    cal_raw = _read_yaml(root / "calendar.yaml", errors)
    if cal_raw is not None:
        try:
            calendar = CalendarData.model_validate(cal_raw)
        except ValidationError as e:
            errors.append(f"calendar.yaml: {e.errors()[0]['loc']} {e.errors()[0]['msg']}")

    contacts: list[Contact] = []
    for item in _read_yaml(root / "contacts.yaml", errors, list) or []:
        try:
            contacts.append(Contact.model_validate(item))
        except ValidationError as e:
            errors.append(f"contacts.yaml: {e.errors()[0]['msg']}")
    faq: list[FaqEntry] = []
    for item in _read_yaml(root / "faq.yaml", errors, list) or []:
        try:
            entry = FaqEntry.model_validate(item)
            faq.append(entry)
            for pid in entry.place_ids:
                if pid not in places:
                    errors.append(f"faq.yaml: {entry.id} references unknown place {pid}")
        except ValidationError as e:
            errors.append(f"faq.yaml: {e.errors()[0]['msg']}")

    if errors or template is None or calendar is None:
        raise KnowledgeError("Knowledge base problems:\n- " + "\n- ".join(errors))
    return KnowledgeBase(
        places=places,
        floors=floors,
        template=template,
        courses=courses,
        course_aliases=course_aliases,
        departments=departments,
        hours=hours,
        calendar=calendar,
        contacts=contacts,
        faq=faq,
        groups=groups,
    )
