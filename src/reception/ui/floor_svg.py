"""Draw a floor as SVG from the knowledge base (same source as navigation)."""

from html import escape

from reception.kb.loader import KnowledgeBase
from reception.kb.models import Place
from reception.speech_format import floor_name

_GENERIC_LABEL = {
    "washroom": "WC",
    "staff_washroom": "Staff WC",
    "water": "W.D",
    "lockers": "Lockers",
    "stairs": "Stairs",
}
_NAME_LABEL = {
    "Gents washroom": "G.W",
    "Ladies washroom": "L.W",
    "Gents staff washroom": "G.S.W",
    "Ladies staff washroom": "L.S.W",
}
_STYLE = """
.floor{fill:#fffaf5;stroke:#6b5a55;stroke-width:4}
.cell rect{stroke:#cdbfb6;stroke-width:1.5;rx:3}
.cat-room rect,.cat-facility rect{fill:#fbf2e2}
.cat-office rect,.cat-reception rect,.cat-department rect{fill:#e4eef8}
.cat-library rect,.cat-cafe rect,.cat-shop rect,.cat-studio rect,.cat-lab rect{fill:#efe5f6}
.cat-washroom rect,.cat-staff_washroom rect{fill:#fde3ea}
.cat-water rect{fill:#dbeafe}
.cat-lockers rect,.cat-stairs rect,.cat-unknown rect{fill:#eeeeee}
.cat-entrance rect{fill:#d9f2e3}
.cell text{font:600 15px 'Source Sans 3',system-ui,sans-serif;fill:#3a2a2c;text-anchor:middle;dominant-baseline:middle}
.cat-unknown text{fill:#888}
.hl rect{fill:#f7d774;stroke:#8a1c2c;stroke-width:5}
.hl text{fill:#6b1220}
.stairs{fill:#d9d4d2;stroke:#7d716d;stroke-width:1.5}
.lift{fill:#fff;stroke:#7d716d;stroke-width:1.5}
.core-text{font:700 14px 'Source Sans 3',system-ui,sans-serif;fill:#4a3d3a;text-anchor:middle;dominant-baseline:middle}
.seat{fill:#f2c14e;stroke:#c48a14;stroke-width:2}
.route{fill:none;stroke:#c0262f;stroke-width:8;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:18 10}
.route-end{fill:#c0262f}
.you{fill:#c0262f}
.you-text{font:700 16px 'Source Sans 3',system-ui,sans-serif;fill:#8a1c2c;text-anchor:end;paint-order:stroke;stroke:#faf7ef;stroke-width:5px}
"""


def _label_lines(p: Place) -> list[str]:
    if p.category in _GENERIC_LABEL:
        return [_NAME_LABEL.get(p.name, _GENERIC_LABEL[p.category])]
    if p.category == "unknown":
        return [p.name.split(" (")[0]]
    if p.room_number and p.category == "room":
        return [p.room_number]
    short = p.name.split(" (")[0]
    lines = [p.room_number] if p.room_number else []
    return [*lines, short]


def _wrap(text: str, max_chars: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def _cell(p: Place, s: float, highlight: set[str]) -> str:
    assert p.rect is not None
    x, y, w, h = p.rect.x * s, p.rect.y * s, p.rect.w * s, p.rect.h * s
    pad = 2.0
    cls = f"cell cat-{p.category}" + (" hl" if p.id in highlight else "")
    font = 15.0
    max_chars = max(3, int((w - 6) / (font * 0.55)))
    lines: list[str] = []
    for part in _label_lines(p):
        lines.extend(_wrap(part, max_chars))
    max_lines = max(1, int((h - 4) / (font * 1.15)))
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(1, max_chars - 1)] + "…"
    cx, cy = x + w / 2, y + h / 2
    first = cy - (len(lines) - 1) * font * 0.575
    text = "".join(
        f'<text x="{cx:.1f}" y="{first + i * font * 1.15:.1f}">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    return (
        f'<g id="place-{escape(p.id)}" class="{cls}"><title>{escape(p.name)}</title>'
        f'<rect x="{x + pad:.1f}" y="{y + pad:.1f}" width="{w - 2 * pad:.1f}" '
        f'height="{h - 2 * pad:.1f}"/>{text}</g>'
    )


def render_floor_svg(
    kb: KnowledgeBase,
    floor: str,
    highlight: list[str] | None = None,
    route: list[tuple[float, float]] | None = None,
    show_kiosk: bool = True,
    scale: float = 10.0,
) -> str:
    """SVG for one floor with optional highlighted places and a route.

    Args:
        kb: Knowledge base.
        floor: Floor id.
        highlight: Place ids to highlight.
        route: Route points in grid units (drawn as a dashed line ending in a dot).
        show_kiosk: Draw "You are here" on the kiosk floor.
        scale: Pixels per grid unit.

    Returns:
        A standalone SVG document string; each place is ``<g id="place-<id>">``.
    """
    s = scale
    tpl = kb.template
    width, height = tpl.width * s, tpl.height * s
    hl = set(highlight or [])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 {width + 20:.0f} '
        f'{height + 20:.0f}" role="img" aria-label="{escape(floor_name(floor))} map">',
        f"<title>{escape(floor_name(floor))}</title><style>{_STYLE}</style>",
        f'<rect class="floor" x="0" y="0" width="{width:.0f}" height="{height:.0f}" rx="10"/>',
    ]
    for st in tpl.staircases:
        sx0, sy0, sx1, sy1 = (float(v) * s for v in st["stairs_box"])  # type: ignore[attr-defined]
        lx0, ly0, lx1, ly1 = (float(v) * s for v in st["lift_box"])  # type: ignore[attr-defined]
        parts.append(
            f'<rect class="stairs" x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}"/>'
            f'<text class="core-text" x="{(sx0 + sx1) / 2}" y="{(sy0 + sy1) / 2}">STAIRCASE</text>'
            f'<rect class="lift" x="{lx0}" y="{ly0}" width="{lx1 - lx0}" height="{ly1 - ly0}"/>'
            f'<text class="core-text" x="{(lx0 + lx1) / 2}" y="{(ly0 + ly1) / 2}">L</text>'
        )
    layout = kb.floors[floor]
    kiosk_here = show_kiosk and floor == tpl.kiosk_floor
    if layout.seating:
        xs = (26, 74) if kiosk_here else (40, 50, 60)
        parts.extend(f'<circle class="seat" cx="{x * s}" cy="{30 * s}" r="18"/>' for x in xs)
    for pid in layout.cell_ids:
        p = kb.places.get(pid)
        if p is not None and p.rect is not None:
            parts.append(_cell(p, s, hl))
    if route and len(route) > 1:
        pts = " ".join(f"{x * s:.1f},{y * s:.1f}" for x, y in route)
        ex, ey = route[-1]
        parts.append(f'<polyline class="route" points="{pts}"/>')
        parts.append(f'<circle class="route-end" cx="{ex * s:.1f}" cy="{ey * s:.1f}" r="12"/>')
    if kiosk_here:
        kx, ky = tpl.kiosk.x * s, tpl.kiosk.y * s
        parts.append(
            f'<g id="you-are-here"><path class="you" d="M{kx} {ky + 4} c-10-14-16-21-16-29 '
            f'a16 16 0 0 1 32 0 c0 8-6 15-16 29z"/><circle cx="{kx}" cy="{ky - 25}" r="6" fill="#fff"/>'
            f'<text class="you-text" x="{kx - 22}" y="{ky + 6}">You are here</text></g>'
        )
    parts.append("</svg>")
    return "".join(parts)
