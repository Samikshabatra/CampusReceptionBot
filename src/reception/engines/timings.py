"""Opening-hours rules: holidays, third Saturdays, vacations, lunch breaks."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal

from reception.kb.models import CalendarData, DayRule, HoursGroup

Reason = Literal["holiday", "third_saturday", "sunday", "vacation", "weekday", "working_saturday"]
_SEARCH_DAYS = 14


class CalendarExpired(Exception):
    """The requested date is outside the calendar's validity window."""


@dataclass(frozen=True)
class DayHours:
    """Hours for one facility group on one date. ``open is None`` means closed."""

    open: time | None
    close: time | None
    lunch: tuple[time, time] | None
    reason: Reason
    holiday_name: str | None = None


@dataclass(frozen=True)
class Status:
    """Open/closed status at a moment."""

    is_open: bool
    on_lunch: bool
    today: DayHours
    next_open: datetime | None
    verified: bool


def is_third_saturday(d: date) -> bool:
    """True when ``d`` is the third Saturday of its month."""
    return d.weekday() == 5 and 15 <= d.day <= 21


def _apply(group: HoursGroup, rule: DayRule, reason: Reason) -> DayHours:
    if rule == "closed":
        return DayHours(None, None, None, reason)
    if rule == "weekday":
        return DayHours(group.weekday[0], group.weekday[1], group.lunch, reason)
    return DayHours(rule[0], rule[1], None, reason)


def _check_valid(d: date, cal: CalendarData) -> None:
    if not (cal.valid_from <= d < cal.valid_until):
        raise CalendarExpired(d.isoformat())


def day_hours(group: HoursGroup, d: date, cal: CalendarData) -> DayHours:
    """Hours for ``group`` on date ``d``.

    Precedence: holiday > working Saturday > third Saturday > vacation > Sunday > weekday.

    Args:
        group: Facility hours group.
        d: The date.
        cal: Academic calendar.

    Returns:
        The day's hours and why.

    Raises:
        CalendarExpired: ``d`` is outside the calendar.
    """
    _check_valid(d, cal)
    for h in cal.holidays:
        if h.date == d:
            return DayHours(None, None, None, "holiday", h.name)
    if d in cal.working_saturdays:
        return _apply(group, "weekday", "working_saturday")
    if is_third_saturday(d):
        return _apply(group, group.third_saturday, "third_saturday")
    if any(v.start <= d <= v.end for v in cal.vacations):
        return _apply(group, group.vacation, "vacation")
    if d.weekday() == 6:
        return _apply(group, group.sunday, "sunday")
    return _apply(group, "weekday", "weekday")


def _open_at(h: DayHours, t: time) -> tuple[bool, bool]:
    if h.open is None or h.close is None or not (h.open <= t < h.close):
        return False, False
    if h.lunch and h.lunch[0] <= t < h.lunch[1]:
        return False, True
    return True, False


def status_at(group: HoursGroup, at: datetime, cal: CalendarData) -> Status:
    """Whether ``group`` is open at ``at``, and when it next opens.

    Args:
        group: Facility hours group.
        at: Timezone-aware moment.
        cal: Academic calendar.

    Returns:
        Status with today's hours and the next opening time (None if open now or
        nothing within two weeks / the calendar).

    Raises:
        CalendarExpired: ``at`` is outside the calendar.
    """
    today = day_hours(group, at.date(), cal)
    is_open, on_lunch = _open_at(today, at.time())
    next_open: datetime | None = None
    if not is_open:
        if on_lunch and today.lunch:
            next_open = datetime.combine(at.date(), today.lunch[1], at.tzinfo)
        elif today.open is not None and at.time() < today.open:
            next_open = datetime.combine(at.date(), today.open, at.tzinfo)
        else:
            d = at.date()
            for _ in range(_SEARCH_DAYS):
                d += timedelta(days=1)
                try:
                    h = day_hours(group, d, cal)
                except CalendarExpired:
                    break
                if h.open is not None:
                    next_open = datetime.combine(d, h.open, at.tzinfo)
                    break
    return Status(is_open, on_lunch, today, next_open, group.verified)
