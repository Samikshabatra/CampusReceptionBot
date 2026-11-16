from collections.abc import Callable
from datetime import date

import networkx as nx
import pytest

from reception.config import AppConfig
from reception.copy import CALENDAR_EXPIRED, FACULTY_LINE, UNVERIFIED_SUFFIX
from reception.engines.courses import (
    course_fees_response,
    course_info_response,
    course_list_response,
)
from reception.engines.info import (
    college_open_response,
    contact_response,
    events_response,
    faculty_response,
    hours_response,
)
from reception.engines.navigation import build_graph
from reception.kb.loader import KnowledgeBase
from reception.types import Response
from tests.conftest import dt


@pytest.fixture(scope="module")
def cfg() -> AppConfig:
    return AppConfig()


@pytest.fixture(scope="module")
def g(kb: KnowledgeBase, cfg: AppConfig) -> nx.Graph:
    return build_graph(kb, cfg)


def test_mca_fees_default(kb: KnowledgeBase) -> None:
    r = course_fees_response(kb, "50", None, None)
    assert "2 lakh 42 thousand rupees" in r.speech
    assert r.speech.endswith("for academic year 2027, as published.")
    assert r.card.kind == "fees"
    assert r.links[0].url.startswith("https://christuniversity.in/courses/")


def test_fee_category_and_year(kb: KnowledgeBase) -> None:
    r = course_fees_response(kb, "50", "nri", 2)
    assert "NRI" in r.speech and "year 2" in r.speech


def test_fee_usd_category(kb: KnowledgeBase) -> None:
    assert "US dollars" in course_fees_response(kb, "50", "oci", 1).speech


def test_not_published(kb: KnowledgeBase) -> None:
    assert "not published" in course_fees_response(kb, "946", None, None).speech.lower()


def test_registration_fee_missing(kb: KnowledgeBase) -> None:
    card = course_fees_response(kb, "50", None, None).card
    assert "contact Admissions" in card.data["registration_fee"]


def test_course_info_cs(kb: KnowledgeBase) -> None:
    r = course_info_response(kb, "50")
    assert "postgraduate" in r.speech and "8th floor" in r.speech
    assert r.card.kind == "course" and r.card.data["description"]


def test_course_info_not_in_block(kb: KnowledgeBase) -> None:
    assert "isn't in Central Block" in course_info_response(kb, "580").speech


def test_course_list(kb: KnowledgeBase) -> None:
    r = course_list_response(kb, "Department of Computer Science", None)
    assert "9" in r.speech and len(r.card.data["items"]) == 9
    assert (
        len(course_list_response(kb, "Department of Computer Science", "PG").card.data["items"])
        == 4
    )


def test_faculty(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    r = faculty_response(kb, g, cfg, None)
    assert r.speech == FACULTY_LINE
    assert r.links[0].url.startswith("https://kp.christuniversity.in")
    assert r.card.data["targets"] == ["faculty_staff_room"]


def test_faculty_other_department(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    assert "4th floor" in faculty_response(kb, g, cfg, "School of Law").speech


def test_contacts(kb: KnowledgeBase) -> None:
    r = contact_response(kb, "admissions")
    assert "plus 9 1, 9 2 4 3 0, 8 0 8 0 0" in r.speech
    urls = [link.url for link in r.links]
    assert "tel:+919243080800" in urls and "mailto:admissions@christuniversity.in" in urls


def test_library_hours_sunday(kb: KnowledgeBase) -> None:
    r = hours_response(kb, "library", dt("2026-11-15 11:00"))
    assert "open now" in r.speech and "10 am to 6 pm" in r.speech


def test_office_closed_holiday(kb: KnowledgeBase) -> None:
    r = hours_response(kb, "accounts_office", dt("2026-11-10 11:00"))
    assert "closed" in r.speech and "Deepavali" in r.speech and "11 November" in r.speech


def test_office_lunch(kb: KnowledgeBase) -> None:
    assert "lunch" in hours_response(kb, "reception", dt("2026-11-04 13:15")).speech


def test_services_suffix(kb: KnowledgeBase) -> None:
    r = hours_response(kb, "xerox_shop", dt("2026-11-04 10:00"))
    assert r.speech.endswith(UNVERIFIED_SUFFIX.strip()) and r.verified is False


def test_hours_calendar_expired(kb: KnowledgeBase) -> None:
    r = hours_response(kb, "library", dt("2027-06-05 10:00"))
    assert r.speech == CALENDAR_EXPIRED and r.handover_reason == "calendar_expired"


def test_college_open_third_saturday(kb: KnowledgeBase) -> None:
    s = college_open_response(kb, dt("2027-01-16 10:00")).speech.lower()
    assert "offices are closed" in s and "library is open" in s


def test_open_day_event(kb: KnowledgeBase) -> None:
    r = events_response(kb, date(2026, 11, 4), "open_day")
    assert "21 November" in r.speech and "and Open Day" in r.speech


def test_upcoming_holidays(kb: KnowledgeBase) -> None:
    r = events_response(kb, date(2026, 11, 4), "holidays")
    assert "Deepavali" in r.speech


MAKERS: list[Callable[..., Response]] = [
    lambda kb, g, cfg: course_fees_response(kb, "50", None, None),
    lambda kb, g, cfg: course_fees_response(kb, "553", "foreign", 4),
    lambda kb, g, cfg: course_info_response(kb, "553"),
    lambda kb, g, cfg: course_info_response(kb, "621"),
    lambda kb, g, cfg: course_list_response(kb, "Department of Psychology", None),
    lambda kb, g, cfg: faculty_response(kb, g, cfg, "Department of Psychology"),
    lambda kb, g, cfg: contact_response(kb, "general"),
    lambda kb, g, cfg: contact_response(kb, "library"),
    lambda kb, g, cfg: contact_response(kb, "all"),
    lambda kb, g, cfg: hours_response(kb, "library", dt("2026-11-04 22:00")),
    lambda kb, g, cfg: hours_response(kb, "offices", dt("2027-01-16 10:00")),
    lambda kb, g, cfg: college_open_response(kb, dt("2026-11-10 10:00")),
    lambda kb, g, cfg: events_response(kb, date(2026, 11, 4), "upcoming"),
    lambda kb, g, cfg: events_response(kb, date(2026, 11, 4), "admissions"),
]


@pytest.mark.parametrize("make", MAKERS)
def test_speech_rules(
    kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig, make: Callable[..., Response]
) -> None:
    s = make(kb, g, cfg).speech
    assert "http" not in s and "&" not in s
    assert len(s.split()) <= cfg.max_speech_words, s


def test_every_course_fee_speech_fits(kb: KnowledgeBase, cfg: AppConfig) -> None:
    for cid in kb.courses:
        s = course_fees_response(kb, cid, None, None).speech
        assert len(s.split()) <= cfg.max_speech_words, (cid, s)
        s = course_info_response(kb, cid).speech
        assert len(s.split()) <= cfg.max_speech_words, (cid, s)
