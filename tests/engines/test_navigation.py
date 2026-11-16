import networkx as nx
import pytest

from reception.config import AppConfig
from reception.engines.navigation import (
    build_graph,
    directions,
    navigation_response,
    nearest_of_category,
    plan_route,
    resolve_places,
)
from reception.kb.loader import KnowledgeBase
from reception.speech_format import floor_name, floor_phrase, place_phrase

START = "G:kiosk"


@pytest.fixture(scope="module")
def cfg() -> AppConfig:
    return AppConfig()


@pytest.fixture(scope="module")
def g(kb: KnowledgeBase, cfg: AppConfig) -> nx.Graph:
    return build_graph(kb, cfg)


def test_floor_names() -> None:
    assert [floor_name(f) for f in ("B", "G", "1", "2", "3", "8", "10")] == [
        "Basement",
        "Ground floor",
        "1st floor",
        "2nd floor",
        "3rd floor",
        "8th floor",
        "10th floor",
    ]
    assert floor_phrase("B") == "in the Basement"
    assert floor_phrase("G") == "on the Ground floor"


def test_place_phrase(kb: KnowledgeBase) -> None:
    assert place_phrase(kb.places["xerox_shop"]) == "The Xerox and Print Shop"
    assert place_phrase(kb.places["room_812"]) == "Room 812"


def test_route_to_xerox(kb: KnowledgeBase, g: nx.Graph) -> None:
    r = plan_route(kb, g, START, "xerox_shop", "lift")
    assert [leg.floor for leg in r.legs] == ["G", "B"]
    assert any("lift" in n for n in r.legs[0].node_ids)
    assert r.legs[-1].node_ids[-1] == "B:xerox_shop"
    assert r.via == "lift"


def test_same_floor_no_lift(kb: KnowledgeBase, g: nx.Graph) -> None:
    r = plan_route(kb, g, START, "accounts_office", "lift")
    assert len(r.legs) == 1 and r.via is None


def test_stairs_preference(kb: KnowledgeBase, g: nx.Graph) -> None:
    r = plan_route(kb, g, START, "library", "stairs")
    assert any("stairs" in n for n in r.legs[0].node_ids) and r.via == "stairs"


def test_whole_floor_target(kb: KnowledgeBase, g: nx.Graph) -> None:
    r = plan_route(kb, g, START, "sbm_2", "lift")
    assert [leg.floor for leg in r.legs] == ["G", "2"]
    assert [
        leg.floor for leg in plan_route(kb, g, START, "dept_computer_science", "lift").legs
    ] == ["G", "8"]


def test_nearest_washroom_on_kiosk_floor(kb: KnowledgeBase, g: nx.Graph) -> None:
    p = nearest_of_category(kb, g, START, "washroom")
    assert p.floor == "2" and p.category == "washroom"  # none on G; 2F ones sit by the lift


def test_xerox_speech(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    r = navigation_response(kb, g, cfg, ["xerox_shop"], "lift")
    assert r.speech.startswith(
        "The Xerox and Print Shop is in the Basement. Take the nearest lift down to the Basement."
    )
    assert r.card.kind == "map" and r.card.data["floors"] == ["G", "B"]
    assert r.card.data["steps"] and r.intent == "navigate"
    assert len(r.speech.split()) <= cfg.max_speech_words


def test_same_floor_speech(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    r = navigation_response(kb, g, cfg, ["accounts_office"], "lift")
    assert r.speech.startswith("The Accounts Office is on this floor")


def test_group_shows_all_primary_first(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    r = navigation_response(kb, g, cfg, ["admissions_office"], "lift")
    assert r.card.data["targets"] == ["admissions_office", "room_110"]
    assert "this floor" in r.speech and "Room 110" in r.speech
    assert len(r.speech.split()) <= cfg.max_speech_words


def test_resolve_group_name(kb: KnowledgeBase) -> None:
    assert [p.id for p in resolve_places(kb, ["media_studies"])] == ["room_1000"]
    assert [p.id for p in resolve_places(kb, ["law"])] == ["sol_4", "sol_5"]
    assert "dept_law" not in kb.places  # Law is on the 4th floor only (team, 2026-11-04)


def test_directions_mention_lift_and_floor(kb: KnowledgeBase, g: nx.Graph) -> None:
    steps = directions(kb, plan_route(kb, g, START, "library", "lift"))
    assert any("lift" in s and "6th floor" in s for s in steps)


def test_unknown_not_in_graph(g: nx.Graph) -> None:
    assert "8:8_ld_1" not in g and "2:2_lt_1" not in g


def test_every_place_reachable(kb: KnowledgeBase, g: nx.Graph) -> None:
    for p in kb.places.values():
        if p.category in ("unknown", "stairs"):
            continue
        r = plan_route(kb, g, START, p.id, "lift")
        assert r.legs, p.id
