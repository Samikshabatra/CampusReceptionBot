"""Pull rooms, places, courses, fee categories and dates out of normalised text."""

import re
from typing import Literal

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from reception.kb.loader import KnowledgeBase
from reception.kb.models import FeeCategory

DateRef = Literal["today", "tomorrow", "saturday", "sunday", "this_week"]
_SHORT_WORD = 3
_ROOM_RE = re.compile(r"\b(c\d{3}|\d{3,4})\b")
_YEAR_LIKE = re.compile(r"^(19|20)\d{2}$")
_COURSE_HINTS = re.compile(
    r"\b(bachelor|master|ba|bsc|msc|ma|mcom|bcom|phd|llb|llm|mba|bba|bca|mca|programme|program|"
    r"course|degree|diploma|doctor)\b"
)
_GENERIC = {
    "washroom": ["washroom", "toilet", "restroom", "rest room", "bathroom", "loo", "lavatory"],
    "water": ["water", "drinking water", "water dispenser", "water cooler"],
    "lift": ["lift", "elevator"],
}
_CATEGORIES: list[tuple[FeeCategory, str]] = [
    ("other_states", r"\b(other|outside) (indian )?states?\b|\bnon karnataka\b"),
    ("karnataka", r"\bkarnataka\b"),
    ("nri", r"\bnri\b|non resident"),
    ("oci", r"\boci\b|overseas citizen"),
    ("saarc", r"\b(saarc|africa|african|pio|asean)\b"),
    ("foreign", r"\b(foreign|international)\b"),
]
_YEARS = {
    1: r"\b(first|1st) year\b|\byear 1\b",
    2: r"\b(second|2nd) year\b|\byear 2\b",
    3: r"\b(third|3rd) year\b|\byear 3\b",
    4: r"\b(fourth|4th) year\b|\byear 4\b",
    5: r"\b(fifth|5th) year\b|\byear 5\b",
}
_DATES: list[tuple[DateRef, str]] = [
    ("tomorrow", r"\btomorrow\b"),
    ("today", r"\b(today|now|right now|currently)\b"),
    ("saturday", r"\bsaturday\b"),
    ("sunday", r"\bsunday\b"),
    ("this_week", r"\bthis week\b"),
]
_STAIRS = re.compile(r"\b(stairs|staircase|steps|stairway)\b")
_DEPT_PREFIX = re.compile(r"^(department of|school of)\s+")


class Entities(BaseModel):
    """Everything extracted from one utterance."""

    room: str | None = None
    place_ids: list[str] = Field(default_factory=list)
    category_request: str | None = None
    course_ids: list[str] = Field(default_factory=list)
    fee_category: FeeCategory | None = None
    year: int | None = None
    department: str | None = None
    date_ref: DateRef | None = None
    prefer_stairs: bool = False


def _clean(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def _word_in(phrase: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


_ALIAS_CACHE: dict[int, list[tuple[str, str]]] = {}


def _place_aliases(kb: KnowledgeBase) -> list[tuple[str, str]]:
    key = id(kb)
    if key not in _ALIAS_CACHE:
        _ALIAS_CACHE[key] = _build_place_aliases(kb)
    return _ALIAS_CACHE[key]


def _build_place_aliases(kb: KnowledgeBase) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for p in kb.places.values():
        if p.category in ("unknown", "stairs", "washroom", "staff_washroom", "water", "lockers"):
            continue
        if p.category == "room" and not p.aliases:
            continue
        names = {*(a.lower() for a in p.aliases), _clean(p.name)}
        if p.spoken_name:
            names.add(_clean(p.spoken_name))
        out.extend((_clean(n), p.id) for n in names if n)
    return out


def _alias_score(alias: str, words: list[str], threshold: int) -> float:
    """Every alias word must match some text word: exactly if short, fuzzily if long."""
    scores = []
    for aw in alias.split():
        if len(aw) <= _SHORT_WORD:
            scores.append(100.0 if aw in words else 0.0)
        else:
            scores.append(max((fuzz.ratio(aw, w) for w in words), default=0.0))
        if scores[-1] < threshold:
            return 0.0
    return min(scores) if scores else 0.0


def _match_places(text: str, kb: KnowledgeBase, threshold: int) -> list[str]:
    scores: dict[str, tuple[float, int]] = {}
    words = text.split()
    for alias, pid in _place_aliases(kb):
        score = _alias_score(alias, words, threshold)
        if score >= threshold:
            best = scores.get(pid, (0.0, 0))
            scores[pid] = max(best, (score, len(alias)))
    if not scores:
        return []
    top = max(scores.values())
    return [pid for pid, s in scores.items() if s[0] >= top[0] and s[1] >= top[1] - 2]


_DEGREES = {
    "bcom": "bachelor of commerce", "mcom": "master of commerce", "bsc": "bachelor of science",
    "msc": "master of science", "ba": "bachelor of arts", "ma": "master of arts",
    "bba": "bachelor of business administration", "mba": "master of business administration",
    "phd": "doctor of philosophy", "llm": "master of laws",
}  # fmt: skip


def _expand_degrees(text: str) -> str:
    """``"bcom accountancy"`` -> ``"bachelor of commerce accountancy"`` for name matching."""
    return " ".join(_DEGREES.get(w, w) for w in text.split())


def _prefer_duration(ids: list[str], text: str, kb: KnowledgeBase) -> list[str]:
    """Split one-year vs regular variants of the same programme using the text."""
    if len(ids) < 2:
        return ids
    one_year = [c for c in ids if "One Year" in kb.courses[c].name]
    regular = [c for c in ids if c not in one_year]
    if one_year and re.search(r"\b(one|1) year\b", text):
        return one_year
    if one_year and regular and re.search(r"\b(two|2) years?\b", text):
        return regular
    return ids


def _match_courses(text: str, kb: KnowledgeBase) -> list[str]:
    hits: list[tuple[int, str]] = []
    for cid, aliases in kb.course_aliases.items():
        for a in aliases:
            if _word_in(_clean(a), text):
                hits.append((len(a), cid))
    if hits:
        longest = max(n for n, _ in hits)
        return _prefer_duration(sorted({cid for n, cid in hits if n == longest}), text, kb)
    if not _COURSE_HINTS.search(text):
        return []
    expanded = _expand_degrees(text)
    scored = []
    for cid, c in kb.courses.items():
        name = _clean(re.sub(r"/\s*Honours(?: with [Rr]esearch)?", "", c.name))
        scored.append((fuzz.token_set_ratio(name, expanded), cid))
    best = max(s for s, _ in scored)
    if best < 85:
        return []
    return [cid for s, cid in sorted(scored, reverse=True) if s >= best - 3][:3]


def _match_department(text: str, kb: KnowledgeBase, place_ids: list[str]) -> str | None:
    best: tuple[int, str] | None = None
    for dept in kb.departments:
        core = _DEPT_PREFIX.sub("", dept.lower())
        parts = [_clean(p) for p in re.split(r",| and ", core)]
        phrases = [_clean(core), *(p for p in parts if len(p) >= 5)]
        hits = [p for p in phrases if p and _word_in(p, text)]
        if hits:
            n = max(len(h) for h in hits)
            if best is None or n > best[0]:
                best = (n, dept)
    if best:
        return best[1]
    for pid in place_ids:
        dept_name = kb.places[pid].department
        if dept_name:
            return dept_name
    return None


def extract_entities(text: str, kb: KnowledgeBase, fuzzy_threshold: int) -> Entities:
    """Extract entities from normalised text.

    Args:
        text: Output of :func:`reception.nlu.normalise.normalise`.
        kb: Knowledge base.
        fuzzy_threshold: Minimum rapidfuzz score for place aliases.

    Returns:
        Extracted entities (empty fields when absent).
    """
    e = Entities()
    for m in _ROOM_RE.finditer(text):
        num = m.group(1)
        before = text[: m.start()].split()[-1:] == ["room"]
        if _YEAR_LIKE.match(num) and not before:
            continue
        e.room = num
        break
    e.place_ids = _match_places(text, kb, fuzzy_threshold)
    for cat, words in _GENERIC.items():
        if any(_word_in(w, text) for w in words):
            e.category_request = cat
            break
    e.course_ids = _match_courses(text, kb)
    for fee_cat, pattern in _CATEGORIES:
        if re.search(pattern, text):
            e.fee_category = fee_cat
            break
    for year, pattern in _YEARS.items():
        if re.search(pattern, text):
            e.year = year
            break
    e.department = _match_department(text, kb, e.place_ids)
    for ref, pattern in _DATES:
        if re.search(pattern, text):
            e.date_ref = ref
            break
    e.prefer_stairs = bool(_STAIRS.search(text))
    return e
