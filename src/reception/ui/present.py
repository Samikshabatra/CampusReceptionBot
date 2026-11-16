"""Turn a Response into what the kiosk screen draws: maps and QR codes."""

import io
from typing import Any

import networkx as nx
import qrcode
import qrcode.image.svg

from reception.config import AppConfig
from reception.engines.navigation import navigation_response
from reception.kb.loader import KnowledgeBase
from reception.speech_format import floor_name
from reception.types import Response
from reception.ui.floor_svg import render_floor_svg


def qr_svg(data: str) -> str:
    """Inline SVG QR code for ``data``."""
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    text = buf.getvalue().decode("utf-8")
    return text[text.index("<svg") :]


def _maps_for(kb: KnowledgeBase, card_data: dict[str, Any]) -> list[dict[str, str]]:
    targets: list[str] = card_data.get("targets", [])
    legs: list[dict[str, Any]] = card_data.get("legs", [])
    floors: list[str] = card_data.get("floors", [])
    maps = []
    for f in floors:
        route = next((leg["points"] for leg in legs if leg["floor"] == f), None)
        hl = [t for t in targets if kb.places[t].floor == f]
        pts = [tuple(p) for p in route] if route else None
        svg = render_floor_svg(kb, f, highlight=hl, route=pts)  # type: ignore[arg-type]
        maps.append(
            {"floor": f, "title": floor_name(f), "subtitle": kb.floors[f].title, "svg": svg}
        )
    return maps


def present(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig, r: Response) -> dict[str, Any]:
    """Serialise a response for the kiosk with rendered maps and QR codes.

    Args:
        kb: Knowledge base.
        g: Navigation graph (for handover routes).
        cfg: App config.
        r: Assistant response.

    Returns:
        ``r`` as JSON-ready dict plus ``maps`` (floor, title, svg) and ``qr`` (label, url, svg).
    """
    out = r.model_dump(mode="json")
    maps: list[dict[str, str]] = []
    if r.card.kind == "map":
        maps = _maps_for(kb, r.card.data)
    elif r.card.kind == "handover" and r.card.data.get("place_ids"):
        nav = navigation_response(kb, g, cfg, list(r.card.data["place_ids"]), "lift")
        maps = _maps_for(kb, nav.card.data)
        out["card"]["data"]["steps"] = nav.card.data["steps"]
    out["maps"] = maps
    out["qr"] = [
        {"label": link.label, "url": link.url, "svg": qr_svg(link.url)} for link in r.links
    ]
    return out
