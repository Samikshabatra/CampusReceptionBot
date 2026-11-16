from datetime import date, time

import pytest

from reception.engines.timings import CalendarExpired, day_hours, status_at
from reception.kb.loader import KnowledgeBase
from tests.conftest import dt


@pytest.fixture(scope="module")
def groups(kb: KnowledgeBase):  # type: ignore[no-untyped-def]
    return kb.hours["offices"], kb.hours["library"], kb.hours["services"], kb.calendar


def test_weekday_office_open(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    assert status_at(off, dt("2026-11-04 10:00"), cal).is_open


def test_lunch(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    s = status_at(off, dt("2026-11-04 13:00"), cal)
    assert not s.is_open and s.on_lunch


def test_close_boundary(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    assert not status_at(off, dt("2026-11-04 17:00"), cal).is_open
    assert status_at(off, dt("2026-11-04 16:59"), cal).is_open


def test_library_before_open(groups) -> None:  # type: ignore[no-untyped-def]
    _, lib, _, cal = groups
    assert not status_at(lib, dt("2026-11-04 07:59"), cal).is_open
    assert status_at(lib, dt("2026-11-04 20:59"), cal).is_open


def test_holiday_closes_both(groups) -> None:  # type: ignore[no-untyped-def]
    off, lib, _, cal = groups
    assert day_hours(off, date(2026, 11, 10), cal).reason == "holiday"
    assert day_hours(lib, date(2026, 11, 8), cal).open is None


def test_compensatory_and_override_saturdays(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    assert day_hours(off, date(2026, 11, 21), cal).open == time(9)
    assert day_hours(off, date(2026, 11, 21), cal).reason == "working_saturday"
    assert day_hours(off, date(2026, 11, 28), cal).reason == "holiday"


def test_third_saturday(groups) -> None:  # type: ignore[no-untyped-def]
    off, lib, _, cal = groups
    assert day_hours(off, date(2027, 1, 16), cal).open is None
    h = day_hours(lib, date(2027, 1, 16), cal)
    assert (h.open, h.close, h.reason) == (time(9), time(18), "third_saturday")


def test_vacation_library_sunday(groups) -> None:  # type: ignore[no-untyped-def]
    off, lib, _, cal = groups
    assert day_hours(lib, date(2026, 12, 27), cal).close == time(17)
    assert day_hours(off, date(2026, 12, 28), cal).open == time(9)


def test_christmas_assumed_holiday(groups) -> None:  # type: ignore[no-untyped-def]
    _, lib, _, cal = groups
    h = day_hours(lib, date(2026, 12, 25), cal)
    assert h.reason == "holiday" and h.holiday_name == "Christmas"


def test_sunday_closed_offices(groups) -> None:  # type: ignore[no-untyped-def]
    off, lib, _, cal = groups
    assert day_hours(off, date(2026, 11, 15), cal).reason == "sunday"
    assert day_hours(lib, date(2026, 11, 15), cal).open == time(10)


def test_services_unverified(groups) -> None:  # type: ignore[no-untyped-def]
    _, _, srv, cal = groups
    assert status_at(srv, dt("2026-11-04 10:00"), cal).verified is False


def test_next_open_after_close(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    assert status_at(off, dt("2026-11-04 18:00"), cal).next_open == dt("2026-11-05 09:00")
    assert status_at(off, dt("2026-11-04 13:30"), cal).next_open == dt("2026-11-04 14:00")


def test_next_open_skips_holiday(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    # Mon 9 Nov 18:00 -> Tue 10 Nov is Deepavali -> Wed 11 Nov 09:00
    assert status_at(off, dt("2026-11-09 18:00"), cal).next_open == dt("2026-11-11 09:00")


def test_calendar_expired(groups) -> None:  # type: ignore[no-untyped-def]
    off, _, _, cal = groups
    with pytest.raises(CalendarExpired):
        status_at(off, dt("2027-06-02 10:00"), cal)
