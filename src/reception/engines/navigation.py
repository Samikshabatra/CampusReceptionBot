"""Routes from the kiosk to any place, with spoken and written directions."""

import math
from dataclasses import dataclass, field
from typing import Any, Literal

import networkx as nx

from reception.config import AppConfig
from reception.kb.loader import KnowledgeBase
from reception.kb.models import FLOOR_ORDER, FLOORS, Place
from reception.speech_format import floor_name, floor_phrase, place_phrase
from reception.types import Card, Response

Prefer = Literal["lift", "stairs"]
RING = ("tl", "tc", "tr", "ml", "mr", "bl", "bc", "br")
NOT_ROUTABLE = {"unknown", "stairs"}
LANDMARK_SKIP = {"unknown", "stairs", "water", "washroom", "staff_washroom", "lockers"}
_STAIRS_PENALTY = 10.0


@dataclass
class RouteLeg:
    """The walked part of a route on one floor."""

    floor: str
    points: list[tuple[float, float]]
    node_ids: list[str]


@dataclass
class Route:
    """A full route, one leg per floor walked."""

    place_id: str
    legs: list[RouteLeg] = field(default_factory=list)
    via: Prefer | None = None


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def build_graph(kb: KnowledgeBase, cfg: AppConfig) -> nx.Graph:
    """Build the walkable graph for the whole building.

    Args:
        kb: Knowledge base.
        cfg: App config (vertical costs).

    Returns:
        Graph with nodes ``"<floor>:<name>"`` carrying ``floor``, ``x``, ``y``.
    """
    g: nx.Graph = nx.Graph()
    tpl = kb.template
    pos = {n.name: (n.x, n.y) for n in tpl.nodes}
    for f in FLOORS:
        for name, (x, y) in pos.items():
            g.add_node(f"{f}:{name}", floor=f, x=x, y=y, kind="template")
        for a, b in tpl.edges:
            g.add_edge(f"{f}:{a}", f"{f}:{b}", weight=_dist(pos[a], pos[b]), kind="walk")
    kf = tpl.kiosk_floor
    kpos = (tpl.kiosk.x, tpl.kiosk.y)
    g.add_node(f"{kf}:{tpl.kiosk.name}", floor=kf, x=kpos[0], y=kpos[1], kind="kiosk")
    for link in tpl.kiosk_links:
        g.add_edge(f"{kf}:{tpl.kiosk.name}", f"{kf}:{link}", weight=_dist(kpos, pos[link]))
    for p in kb.places.values():
        if p.rect is None or p.category in NOT_ROUTABLE:
            continue
        c = p.rect.center
        ring = min(RING, key=lambda r: _dist(c, pos[r]))
        node = f"{p.floor}:{p.id}"
        g.add_node(node, floor=p.floor, x=c[0], y=c[1], kind="place")
        g.add_edge(node, f"{p.floor}:{ring}", weight=_dist(c, pos[ring]), kind="walk")
    for lower, upper in zip(FLOORS, FLOORS[1:], strict=False):
        for name in ("lift_top", "lift_bottom"):
            g.add_edge(
                f"{lower}:{name}", f"{upper}:{name}", weight=cfg.lift_cost_per_floor, kind="lift"
            )
        for name in ("stairs_top", "stairs_bottom"):
            g.add_edge(
                f"{lower}:{name}",
                f"{upper}:{name}",
                weight=cfg.stairs_cost_per_floor,
                kind="stairs",
            )
    return g


def _weight(prefer: Prefer) -> Any:
    def w(u: str, v: str, d: dict[str, Any]) -> float:
        base = float(d["weight"])
        if prefer == "stairs" and d.get("kind") == "lift":
            return base * _STAIRS_PENALTY
        return base

    return w


def _target_nodes(kb: KnowledgeBase, place: Place) -> list[str]:
    if place.whole_floor or place.rect is None:
        arrivals = ("lift_top", "lift_bottom", "stairs_top", "stairs_bottom")
        return [f"{place.floor}:{n}" for n in arrivals]
    return [f"{place.floor}:{place.id}"]


def plan_route(kb: KnowledgeBase, g: nx.Graph, start: str, place_id: str, prefer: Prefer) -> Route:
    """Shortest route from ``start`` to a place.

    Args:
        kb: Knowledge base.
        g: Graph from :func:`build_graph`.
        start: Start node id (the kiosk).
        place_id: Destination place id.
        prefer: ``lift`` or ``stairs``.

    Returns:
        The route; a whole-floor place on the start floor gives one leg holding only ``start``.
    """
    place = kb.places[place_id]
    start_floor = g.nodes[start]["floor"]
    if (place.whole_floor or place.rect is None) and place.floor == start_floor:
        x, y = g.nodes[start]["x"], g.nodes[start]["y"]
        return Route(place_id, [RouteLeg(start_floor, [(x, y)], [start])], None)
    best: list[str] | None = None
    best_len = math.inf
    for t in _target_nodes(kb, place):
        length, path = nx.single_source_dijkstra(g, start, t, weight=_weight(prefer))
        if length < best_len:
            best, best_len = path, length
    assert best is not None
    legs: list[RouteLeg] = []
    via: Prefer | None = None
    for a, b in zip(best, best[1:], strict=False):
        kind = g.edges[a, b].get("kind")
        if kind in ("lift", "stairs"):
            via = kind
    walked = {start_floor, place.floor}
    for n in best:
        f = g.nodes[n]["floor"]
        if f not in walked:
            continue  # riding the lift / climbing past this floor
        if not legs or legs[-1].floor != f:
            legs.append(RouteLeg(f, [], []))
        legs[-1].node_ids.append(n)
        legs[-1].points.append((g.nodes[n]["x"], g.nodes[n]["y"]))
    return Route(place_id, legs, via)


def resolve_places(kb: KnowledgeBase, place_ids: list[str]) -> list[Place]:
    """Expand ids and group names to places; a grouped place brings its whole group.

    Args:
        kb: Knowledge base.
        place_ids: Place ids or group names.

    Returns:
        Places, primary first within each group, without duplicates.
    """
    out: list[str] = []
    for pid in place_ids:
        members: list[str]
        if pid in kb.groups:
            members = kb.groups[pid]
        elif pid in kb.places and kb.places[pid].group:
            members = kb.groups[kb.places[pid].group]  # type: ignore[index]
        elif pid in kb.places:
            members = [pid]
        else:
            members = []
        out.extend(m for m in members if m not in out)
    return [kb.places[i] for i in out]


def nearest_of_category(kb: KnowledgeBase, g: nx.Graph, start: str, category: str) -> Place:
    """Closest routable place of a category (e.g. ``washroom``, ``water``).

    Args:
        kb: Knowledge base.
        g: Graph.
        start: Start node.
        category: Place category.

    Returns:
        The nearest matching place.
    """
    lengths = nx.single_source_dijkstra_path_length(g, start, weight="weight")
    candidates = [
        p
        for p in kb.places.values()
        if p.category == category and f"{p.floor}:{p.id}" in lengths and p.primary
    ]
    return min(candidates, key=lambda p: lengths[f"{p.floor}:{p.id}"])


def side_of(place: Place) -> str:
    """Map-relative side (``left``/``right``/``top``/``bottom``/``centre``) of a place."""
    if place.rect is None:
        return "centre"
    cx, cy = place.rect.center
    dx, dy = cx - 50, (cy - 30) * (100 / 60)
    if abs(dx) < 8 and abs(dy) < 8:
        return "centre"
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "bottom" if dy > 0 else "top"


def landmark_of(kb: KnowledgeBase, place: Place) -> Place | None:
    """Nearest other named place on the same floor, to anchor directions."""
    if place.rect is None:
        return None
    c = place.rect.center
    others = [
        p
        for p in kb.places.values()
        if p.floor == place.floor
        and p.id != place.id
        and p.rect is not None
        and p.category not in LANDMARK_SKIP
        and (place.group is None or p.group != place.group)
    ]
    named = [p for p in others if p.category != "room"] or others
    if not named:
        return None
    return min(named, key=lambda p: _dist(c, p.rect.center))  # type: ignore[union-attr]


def _position_phrase(kb: KnowledgeBase, place: Place) -> str:
    side = side_of(place)
    lm = landmark_of(kb, place)
    where = "in the centre" if side == "centre" else f"on the {side} side"
    return f"{where}, near {place_phrase(lm, capital=False)}" if lm else where


def directions(kb: KnowledgeBase, route: Route) -> list[str]:
    """Written step-by-step directions for the screen."""
    place = kb.places[route.place_id]
    steps: list[str] = []
    first, last = route.legs[0], route.legs[-1]
    if first.floor != last.floor:
        mode = "lift" if route.via == "lift" else "stairs"
        node = first.node_ids[-1].split(":", 1)[1]
        which = "nearest" if "kiosk" in first.node_ids[0] else node.split("_")[-1]
        updown = "up" if FLOOR_ORDER[last.floor] > FLOOR_ORDER[first.floor] else "down"
        steps.append(f"Walk to the {which} {mode}.")
        steps.append(f"Take the {mode} {updown} to the {floor_name(last.floor)}.")
    if place.whole_floor or place.rect is None:
        steps.append(f"{place_phrase(place)} occupies the {floor_name(place.floor)}.")
    else:
        steps.append(f"Follow the corridor to the {side_of(place)} side.")
        steps.append(f"{place_phrase(place)} is {_position_phrase(kb, place)}.")
    return steps


def _speech_for(kb: KnowledgeBase, route: Route, start_floor: str) -> str:
    place = kb.places[route.place_id]
    phrase = place_phrase(place)
    if place.floor == start_floor:
        if place.whole_floor or place.rect is None:
            return f"{phrase} is on this floor. You're here."
        return f"{phrase} is on this floor, {_position_phrase(kb, place)}."
    mode = "the nearest lift" if route.via != "stairs" else "the stairs"
    updown = "up" if FLOOR_ORDER[place.floor] > FLOOR_ORDER[start_floor] else "down"
    dest = floor_name(place.floor)
    text = f"{phrase} is {floor_phrase(place.floor)}. Take {mode} {updown} to the {dest}."
    if not (place.whole_floor or place.rect is None):
        text += f" It's {_position_phrase(kb, place)}."
    return text


def _leg_dict(leg: RouteLeg) -> dict[str, Any]:
    return {"floor": leg.floor, "points": [list(p) for p in leg.points], "node_ids": leg.node_ids}


def navigation_response(
    kb: KnowledgeBase,
    g: nx.Graph,
    cfg: AppConfig,
    place_ids: list[str],
    prefer: Prefer,
    confidence: float = 1.0,
) -> Response:
    """Speech + map card for a navigation request.

    Args:
        kb: Knowledge base.
        g: Graph.
        cfg: Config (kiosk node).
        place_ids: Requested place ids or group names.
        prefer: ``lift`` or ``stairs``.
        confidence: Intent confidence to report.

    Returns:
        A ``map`` card response; extra group members are mentioned in one short sentence.
    """
    places = resolve_places(kb, place_ids)
    start = cfg.kiosk_node
    start_floor = g.nodes[start]["floor"]
    main = places[0]
    route = plan_route(kb, g, start, main.id, prefer)
    speech = _speech_for(kb, route, start_floor)
    for other in places[1:2]:
        if other.whole_floor and main.whole_floor:
            speech += f" It continues {floor_phrase(other.floor)}."
        elif other.room_number:
            speech += f" Also in Room {other.room_number}, {floor_phrase(other.floor)}."
        else:
            speech += f" Also: {place_phrase(other, capital=False)}, {floor_phrase(other.floor)}."
    floors = [leg.floor for leg in route.legs]
    for other in places[1:]:
        if other.floor not in floors:
            floors.append(other.floor)
    return Response(
        speech=speech,
        card=Card(
            kind="map",
            data={
                "targets": [p.id for p in places],
                "target_names": [p.name for p in places],
                "legs": [_leg_dict(leg) for leg in route.legs],
                "steps": directions(kb, route),
                "floors": floors,
                "via": route.via,
                "start": start,
            },
        ),
        sources=["floor_map"],
        intent="navigate",
        confidence=confidence,
    )
