from pathlib import Path

import pytest
import yaml

from reception.kb.courses_build import (
    clean_courses,
    normalise_duration,
    parse_fee,
    read_courses,
    write_courses,
)
from reception.kb.models import Course, FeeValue

CSV = Path("data/raw/CHRIST_Central_Campus_Courses.csv")


@pytest.fixture(scope="module")
def built() -> tuple[list[Course], list[str]]:
    departments = yaml.safe_load(Path("knowledge/departments.yaml").read_text(encoding="utf-8"))
    return clean_courses(CSV, departments)


def test_parse_fee_variants() -> None:
    assert parse_fee("1,31,000 INR") == FeeValue(
        amount=131000, currency="INR", status="published", raw="1,31,000 INR"
    )
    assert parse_fee("2,375 USD").amount == 2375
    assert parse_fee("2500 EUR").currency == "EUR"
    assert parse_fee("Not Applicable").status == "not_applicable"
    assert parse_fee("Not Published").status == "not_published"
    modular = (
        "Modular Programme: Rs.7000 per course/paper (Credit-based Interdisciplinary curriculum)"
    )
    assert parse_fee(modular).status == "other"


def test_normalise_duration() -> None:
    assert normalise_duration("1 Yrs") == "1 year"
    assert normalise_duration("1 Years") == "1 year"
    assert normalise_duration("4 Yrs") == "4 years"
    assert normalise_duration("3 Years / 4 Years (Honours)") == "3 years / 4 years (Honours)"
    assert normalise_duration("Not Published") is None


def test_clean_courses_fixes(built: tuple[list[Course], list[str]]) -> None:
    courses, report = built
    by_id = {c.id: c for c in courses}
    assert len(courses) == 153
    assert by_id["486"].name == "Master of Science (Forensic Science)"
    assert by_id["486"].verified is False
    assert all("�" not in c.name + (c.description or "") for c in courses)
    assert by_id["553"].registration_fee is None
    assert by_id["50"].fees[1]["karnataka"].amount == 242000
    assert by_id["50"].location_hint == "dept_computer_science"
    assert by_id["580"].location_hint == "not_in_central_block"
    assert by_id["633"].description is None
    assert by_id["920"].duration is None and by_id["920"].semesters is None
    assert by_id["946"].fees[1]["karnataka"].status == "not_published"
    assert sum(c.department == "Department of Computer Science" for c in courses) == 9
    assert not any("fee_structure" in k for k in Course.model_fields)
    assert any("486" in line for line in report)


def test_registration_fee_cleaned(built: tuple[list[Course], list[str]]) -> None:
    fees = {c.registration_fee for c in built[0]} - {None}
    assert fees and all(not f.startswith("of ") and f != "&nbsp;" for f in fees)


def test_every_department_mapped(built: tuple[list[Course], list[str]]) -> None:
    assert all(c.location_hint is not None for c in built[0])


def test_courses_json_roundtrip(built: tuple[list[Course], list[str]], tmp_path: Path) -> None:
    out = tmp_path / "courses.json"
    write_courses(built[0], out)
    again = read_courses(out)
    assert again == built[0]
