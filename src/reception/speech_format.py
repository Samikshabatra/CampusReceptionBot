"""Turn facts into short, speakable phrases."""

import re
from datetime import date, time

from reception.kb.models import Place

_ORDINAL = {1: "st", 2: "nd", 3: "rd"}


def speak_inr(amount: int) -> str:
    """Indian grouping: ``242000`` -> ``"2 lakh 42 thousand rupees"``."""
    crore, rest = divmod(amount, 10_000_000)
    lakh, rest = divmod(rest, 100_000)
    thousand, units = divmod(rest, 1000)
    parts = []
    if crore:
        parts.append(f"{crore} crore")
    if lakh:
        parts.append(f"{lakh} lakh")
    if thousand:
        parts.append(f"{thousand} thousand")
    if units or not parts:
        parts.append(str(units))
    return " ".join(parts) + " rupees"


def speak_money(amount: int, currency: str) -> str:
    """Speak an amount in its currency."""
    if currency == "INR":
        return speak_inr(amount)
    unit = {"USD": "US dollars", "EUR": "euros"}.get(currency, currency)
    return f"{amount:,} {unit}"


def speak_phone(number: str) -> str:
    """``"+91 80 4012 9100"`` -> ``"plus 9 1, 8 0, 4 0 1 2, 9 1 0 0"``."""
    groups = []
    for chunk in number.split():
        prefix = "plus " if chunk.startswith("+") else ""
        groups.append(prefix + " ".join(d for d in chunk if d.isdigit()))
    return ", ".join(groups)


def speak_time(t: time) -> str:
    """``time(13)`` -> ``"1 pm"``; ``time(12)`` -> ``"12 noon"``."""
    if t.hour == 12 and t.minute == 0:
        return "12 noon"
    h = t.hour % 12 or 12
    suffix = "am" if t.hour < 12 else "pm"
    return f"{h} {suffix}" if t.minute == 0 else f"{h}:{t.minute:02d} {suffix}"


def speak_date(d: date) -> str:
    """``date(2026, 11, 21)`` -> ``"21 November"``."""
    return f"{d.day} {d.strftime('%B')}"


def speak_range(start: date, end: date) -> str:
    """``"21 November"`` or ``"21 November to 22 November"``."""
    if start == end:
        return speak_date(start)
    return f"{speak_date(start)} to {speak_date(end)}"


def speakable(text: str) -> str:
    """Replace symbols TTS reads badly (``&``, `` / ``)."""
    return re.sub(r"\s*/\s*", " and ", text.replace(" & ", " and ").replace("&", " and "))


def floor_name(f: str) -> str:
    """``"B"`` -> ``"Basement"``, ``"G"`` -> ``"Ground floor"``, ``"8"`` -> ``"8th floor"``."""
    if f == "B":
        return "Basement"
    if f == "G":
        return "Ground floor"
    n = int(f)
    suffix = "th" if 10 <= n % 100 <= 20 else _ORDINAL.get(n % 10, "th")
    return f"{n}{suffix} floor"


def floor_phrase(f: str) -> str:
    """``"in the Basement"`` / ``"on the 8th floor"``."""
    return f"{'in' if f == 'B' else 'on'} the {floor_name(f)}"


def place_phrase(p: Place, capital: bool = True) -> str:
    """Spoken name with an article where natural: ``"The Xerox and Print Shop"``."""
    name = p.spoken_name or p.name
    if not p.article:
        return name
    return f"{'The' if capital else 'the'} {name}"
