import xml.etree.ElementTree as ET

from reception.kb.loader import KnowledgeBase
from reception.ui.floor_svg import render_floor_svg

NS = "{http://www.w3.org/2000/svg}"


def _ids(svg: str) -> dict[str, ET.Element]:
    root = ET.fromstring(svg)
    return {el.get("id"): el for el in root.iter() if el.get("id")}  # type: ignore[misc]


def test_svg_parses_and_has_every_place(kb: KnowledgeBase) -> None:
    for floor in kb.floors:
        svg = render_floor_svg(kb, floor)
        ids = _ids(svg)
        for p in kb.places.values():
            if p.floor == floor and p.rect is not None:
                assert f"place-{p.id}" in ids, (floor, p.id)


def test_highlight_and_route(kb: KnowledgeBase) -> None:
    svg = render_floor_svg(kb, "B", highlight=["xerox_shop"], route=[(65, 40), (50, 47), (83, 47)])
    ids = _ids(svg)
    assert "hl" in (ids["place-xerox_shop"].get("class") or "")
    poly = [
        el for el in ET.fromstring(svg).iter(f"{NS}polyline") if "route" in (el.get("class") or "")
    ]
    assert len(poly) == 1 and len(poly[0].get("points", "").split()) == 3


def test_kiosk_marker_only_on_kiosk_floor(kb: KnowledgeBase) -> None:
    assert "you-are-here" in _ids(render_floor_svg(kb, "G"))
    assert "you-are-here" not in _ids(render_floor_svg(kb, "8"))


def test_unknown_cells_marked(kb: KnowledgeBase) -> None:
    ids = _ids(render_floor_svg(kb, "8"))
    assert "cat-unknown" in (ids["place-8_ld_1"].get("class") or "")


def test_labels_escape_ampersand(kb: KnowledgeBase) -> None:
    ET.fromstring(render_floor_svg(kb, "B"))  # "Lost & Found" must be escaped
