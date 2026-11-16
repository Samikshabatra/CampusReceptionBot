"""Clean the raw course CSV into verified course records."""

import csv
import json
import re
from pathlib import Path

from reception.kb.models import FEE_CATEGORIES, FEE_CATEGORY_LABELS, Course, FeeValue

_FEE_RE = re.compile(r"^([\d,]+)\s*(INR|USD|EUR)$")
_DURATION_RE = re.compile(r"(\d+)\s*(?:Yrs|Years|Year|Yr)\b", re.IGNORECASE)
_JUNK_REG_FEES = {"", "&nbsp;", "of", "Not Published"}
_FORENSIC_PREFIX = "M.Sc., Forensic science"
_BAD_Y2_DEADLINE = "On or before March 15, 2027"


def parse_fee(raw: str) -> FeeValue:
    """Parse a fee cell such as ``"1,31,000 INR"``.

    Args:
        raw: Cell text.

    Returns:
        Structured fee value; unparseable text gets status ``other``.
    """
    text = raw.strip()
    if text == "Not Applicable":
        return FeeValue(amount=None, currency=None, status="not_applicable", raw=text)
    if text == "Not Published":
        return FeeValue(amount=None, currency=None, status="not_published", raw=text)
    m = _FEE_RE.match(text)
    if m:
        return FeeValue(
            amount=int(m.group(1).replace(",", "")),
            currency=m.group(2),  # type: ignore[arg-type]
            status="published",
            raw=text,
        )
    return FeeValue(amount=None, currency=None, status="other", raw=text)


def normalise_duration(raw: str) -> str | None:
    """Normalise ``"1 Yrs"`` / ``"1 Years"`` to ``"1 year"``.

    Args:
        raw: Duration text from the CSV.

    Returns:
        Normalised duration, or None when not published.
    """
    text = raw.strip()
    if not text or text == "Not Published":
        return None

    def repl(m: re.Match[str]) -> str:
        n = int(m.group(1))
        return f"{n} year" if n == 1 else f"{n} years"

    return _DURATION_RE.sub(repl, text)


def _clean_text(text: str) -> str:
    return " ".join(text.replace("�", "'").split())


def _is_self_repeat(description: str, name: str) -> bool:
    d = " ".join(description.split()).lower()
    n = " ".join(name.split()).lower()
    return bool(n) and d in (f"{n} {n}", n)


def _clean_registration_fee(raw: str) -> str | None:
    reg = raw.strip()
    if reg in _JUNK_REG_FEES:
        return None
    return reg[3:].strip() if reg.startswith("of ") else reg


def clean_courses(csv_path: Path, departments: dict[str, str]) -> tuple[list[Course], list[str]]:
    """Read and clean the course CSV.

    Args:
        csv_path: Path to the raw CSV.
        departments: Department name -> location id or ``not_in_central_block``.

    Returns:
        Cleaned courses and a human-readable build report.
    """
    report: list[str] = []
    courses: list[Course] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        pid = row["Programme ID"].strip()
        notes: list[str] = []
        verified = True
        name = _clean_text(row["Course Name"])
        description: str | None = _clean_text(row["Course Description"]) or None
        if not name:
            verified = False
            if description and description.startswith(_FORENSIC_PREFIX):
                name = "Master of Science (Forensic Science)"
            else:
                name = f"Programme {pid}"
            notes.append("Name missing in source; inferred.")
            report.append(f"{pid}: empty name -> '{name}' (unverified)")
        if description and _is_self_repeat(description, name):
            description = None
            report.append(f"{pid}: description only repeats the name -> treated as missing")

        fees: dict[int, dict] = {}
        deadlines: dict[int, str] = {}
        for year in range(1, 6):
            cells = {
                cat: parse_fee(row[f"Year {year} Fees - {FEE_CATEGORY_LABELS[cat]}"])
                for cat in FEE_CATEGORIES
            }
            if any(v.status != "not_applicable" for v in cells.values()):
                fees[year] = cells
            deadline = row[f"Year {year} Payment Deadline"].strip()
            if deadline and deadline != "Not Applicable":
                deadlines[year] = deadline
        if deadlines.get(2) == _BAD_Y2_DEADLINE:
            notes.append("Year-2 deadline precedes the 2027 academic year; kept as published.")
            report.append(f"{pid}: Year-2 deadline 'March 15, 2027' looks wrong (kept)")

        semesters = row["Number of Semesters"].strip()
        department = row["Department Name"].strip()
        courses.append(
            Course(
                id=pid,
                name=name,
                level=row["Course Level"].strip(),  # type: ignore[arg-type]
                duration=normalise_duration(row["Course Duration"]),
                semesters=None if semesters == "Not Published" else semesters,
                description=description,
                department=department,
                school=row["School Name"].strip(),
                academic_year=row["Academic Year"].strip(),
                registration_fee=_clean_registration_fee(row["Admission Registration Fee"]),
                fees=fees,
                deadlines=deadlines,
                url=row["Course Information URL"].strip(),
                verified=verified,
                location_hint=departments.get(department),
                notes=notes,
            )
        )
    report.append("Dropped column 'Fee Structure URL' (wrong in 150/153 rows).")
    return courses, report


def write_courses(courses: list[Course], path: Path) -> None:
    """Write courses as JSON.

    Args:
        courses: Courses to write.
        path: Output file.
    """
    data = [c.model_dump(mode="json") for c in courses]
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def read_courses(path: Path) -> list[Course]:
    """Read courses written by :func:`write_courses`.

    Args:
        path: JSON file.

    Returns:
        The courses.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Course.model_validate(d) for d in data]
