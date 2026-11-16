"""Pydantic models for every knowledge-base record."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field

Floor = Literal["B", "G", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
FLOORS: tuple[Floor, ...] = ("B", "G", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10")
FLOOR_ORDER: dict[str, int] = {f: i - 1 for i, f in enumerate(FLOORS)}


class Rect(BaseModel):
    """Axis-aligned rectangle on a floor's 100 x 60 grid."""

    x: float
    y: float
    w: float
    h: float

    @property
    def center(self) -> tuple[float, float]:
        """Centre point."""
        return (self.x + self.w / 2, self.y + self.h / 2)


class Place(BaseModel):
    """Anything a visitor can be directed to (or that is drawn on the map)."""

    id: str
    name: str
    spoken_name: str | None = None
    article: bool = True
    aliases: list[str] = Field(default_factory=list)
    category: str
    floor: Floor
    primary: bool = True
    group: str | None = None
    hours_group: str | None = None
    department: str | None = None
    room_number: str | None = None
    whole_floor: bool = False
    rect: Rect | None = None


class FloorLayout(BaseModel):
    """One floor's title, cells and decorations."""

    floor: Floor
    title: str
    seating: bool = False
    cell_ids: list[str] = Field(default_factory=list)


class TemplateNode(BaseModel):
    """A navigation node in the per-floor template."""

    name: str
    x: float
    y: float


class FloorTemplate(BaseModel):
    """Corridor ring, lifts, stairs and the kiosk, shared by all floors."""

    width: float
    height: float
    nodes: list[TemplateNode]
    edges: list[tuple[str, str]]
    staircases: list[dict[str, object]]
    kiosk: TemplateNode
    kiosk_floor: Floor
    kiosk_links: list[str]


Span = tuple[time, time]
DayRule = Span | Literal["closed", "weekday"]


class HoursGroup(BaseModel):
    """Opening-hours rules for a group of facilities."""

    name: str
    verified: bool
    weekday: Span
    lunch: Span | None = None
    third_saturday: DayRule
    sunday: DayRule
    vacation: DayRule


class Holiday(BaseModel):
    """A closed day."""

    date: date
    name: str
    assumed: bool = False


class Vacation(BaseModel):
    """An inclusive vacation date range."""

    name: str
    start: date
    end: date


class Event(BaseModel):
    """A visitor-relevant calendar event."""

    name: str
    start: date
    end: date
    kind: Literal["open_day", "admissions", "exam", "fest", "ceremony", "other"]
    place: str = "Bangalore Central Campus"


class CalendarData(BaseModel):
    """Academic calendar facts used by the timings engine."""

    valid_from: date
    valid_until: date
    note: str = ""
    holidays: list[Holiday]
    working_saturdays: list[date]
    vacations: list[Vacation]
    events: list[Event]


class Contact(BaseModel):
    """A phone number, email or link."""

    id: str
    label: str
    kind: Literal["phone", "email", "url"]
    value: str
    topic: Literal["general", "admissions", "library", "faculty"]


class FaqEntry(BaseModel):
    """A short verified question/answer pair."""

    id: str
    question: str
    answer: str
    place_ids: list[str] = Field(default_factory=list)


FeeCategory = Literal["karnataka", "other_states", "nri", "oci", "saarc", "foreign"]
FEE_CATEGORIES: tuple[FeeCategory, ...] = (
    "karnataka",
    "other_states",
    "nri",
    "oci",
    "saarc",
    "foreign",
)
FEE_CATEGORY_LABELS: dict[FeeCategory, str] = {
    "karnataka": "Karnataka",
    "other_states": "Other Indian States",
    "nri": "NRI",
    "oci": "OCI",
    "saarc": "SAARC/Africa/PIO/ASEAN",
    "foreign": "Other Foreign Nationals",
}


class FeeValue(BaseModel):
    """One fee cell from the course table."""

    amount: int | None
    currency: Literal["INR", "USD", "EUR"] | None
    status: Literal["published", "not_applicable", "not_published", "other"]
    raw: str


class Course(BaseModel):
    """A cleaned programme record."""

    id: str
    name: str
    level: Literal["UG", "PG", "PhD", "Certificate / Executive"]
    duration: str | None
    semesters: str | None
    description: str | None
    department: str
    school: str
    academic_year: str
    registration_fee: str | None
    fees: dict[int, dict[FeeCategory, FeeValue]]
    deadlines: dict[int, str]
    url: str
    verified: bool = True
    location_hint: str | None = None
    notes: list[str] = Field(default_factory=list)
