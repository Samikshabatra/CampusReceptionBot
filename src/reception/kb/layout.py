"""Expand a floor layout (rows of cells) into rectangles on the 100 x 60 grid."""

from collections import defaultdict
from typing import Any

from reception.kb.models import Rect

GENERIC_TOKENS: dict[str, tuple[str, str]] = {
    "gw": ("Gents washroom", "washroom"),
    "lw": ("Ladies washroom", "washroom"),
    "washroom": ("Washroom", "washroom"),
    "gsw": ("Gents staff washroom", "staff_washroom"),
    "lsw": ("Ladies staff washroom", "staff_washroom"),
    "wd": ("Water dispenser", "water"),
    "lockers": ("Lockers", "lockers"),
    "staircase": ("Staircase", "stairs"),
    "fw": ("F.W (meaning unconfirmed)", "unknown"),
    "ld": ("L.D (meaning unconfirmed)", "unknown"),
    "lt": ("L.T (meaning unconfirmed)", "unknown"),
}
GAP = "gap"


def cell_id(floor: str, token: str, counters: dict[str, int]) -> str:
    """Map a layout token to a place id.

    Args:
        floor: Floor id.
        token: Token as written in the layout file.
        counters: Running count per generic token (mutated).

    Returns:
        Place id: ``room_<n>`` for room numbers, ``<floor>_<token>_<n>`` for generic
        tokens, the token itself for named places.
    """
    t = str(token)
    if t[:1].isdigit() or (t[:1] in "cC" and t[1:].isdigit()):
        return f"room_{t.lower()}"
    if t in GENERIC_TOKENS:
        counters[t] += 1
        return f"{floor}_{t}_{counters[t]}"
    return t


def expand_layout(raw: dict[str, Any]) -> list[tuple[str, Rect]]:
    """Expand rows of cells into (place id, rect) pairs.

    Cells split their row box evenly by ``span`` (default 1). A cell id used more than
    once on a floor is merged into one bounding rectangle. ``gap`` cells are skipped.

    Args:
        raw: Parsed floor YAML (``floor``, ``rows``, optional ``extras``).

    Returns:
        Place ids with rectangles, in layout order.
    """
    floor = str(raw["floor"])
    counters: dict[str, int] = defaultdict(int)
    boxes: dict[str, list[tuple[float, float, float, float]]] = {}
    for row in raw.get("rows", []):
        x0, y0, x1, y1 = (float(v) for v in row["box"])
        vertical = row["direction"] == "vertical"
        cells = [c if isinstance(c, dict) else {"id": c} for c in row["cells"]]
        total = sum(float(c.get("span", 1)) for c in cells)
        length = (y1 - y0) if vertical else (x1 - x0)
        pos = y0 if vertical else x0
        for c in cells:
            size = length * float(c.get("span", 1)) / total
            token = str(c["id"])
            if token != GAP:
                pid = cell_id(floor, token, counters)
                box = (x0, pos, x1, pos + size) if vertical else (pos, y0, pos + size, y1)
                boxes.setdefault(pid, []).append(box)
            pos += size
    for extra in raw.get("extras", []):
        bx = tuple(float(v) for v in extra["box"])
        boxes.setdefault(str(extra["id"]), []).append(bx)  # type: ignore[arg-type]
    out: list[tuple[str, Rect]] = []
    for pid, bs in boxes.items():
        ax0 = min(b[0] for b in bs)
        ay0 = min(b[1] for b in bs)
        ax1 = max(b[2] for b in bs)
        ay1 = max(b[3] for b in bs)
        out.append((pid, Rect(x=ax0, y=ay0, w=ax1 - ax0, h=ay1 - ay0)))
    return out
