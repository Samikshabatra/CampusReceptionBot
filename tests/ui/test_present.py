import networkx as nx
import pytest

from reception.config import AppConfig
from reception.dialogue.handover import handover_response
from reception.engines.courses import course_fees_response
from reception.engines.navigation import build_graph, navigation_response
from reception.kb.loader import KnowledgeBase
from reception.ui.present import present, qr_svg


@pytest.fixture(scope="module")
def cfg() -> AppConfig:
    return AppConfig()


@pytest.fixture(scope="module")
def g(kb: KnowledgeBase, cfg: AppConfig) -> nx.Graph:
    return build_graph(kb, cfg)


def test_xerox_two_maps(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    out = present(kb, g, cfg, navigation_response(kb, g, cfg, ["xerox_shop"], "lift"))
    assert [m["floor"] for m in out["maps"]] == ["G", "B"]
    assert 'id="place-xerox_shop" class="cell cat-shop hl"' in out["maps"][1]["svg"]
    assert "you-are-here" in out["maps"][0]["svg"] and 'class="route"' in out["maps"][0]["svg"]
    assert out["maps"][1]["title"] == "Basement"
    assert out["maps"][1]["subtitle"] == "Services & Facilities"


def test_group_extra_floor_highlighted(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    out = present(kb, g, cfg, navigation_response(kb, g, cfg, ["admissions_office"], "lift"))
    floors = [m["floor"] for m in out["maps"]]
    assert floors == ["G", "1"]
    assert "place-room_110" in out["maps"][1]["svg"] and " hl" in out["maps"][1]["svg"]


def test_links_get_qr(kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig) -> None:
    out = present(kb, g, cfg, course_fees_response(kb, "50", None, None))
    assert out["qr"] and out["qr"][0]["svg"].lstrip().startswith("<svg")
    assert out["maps"] == []


def test_urgent_handover_shows_health_centre(
    kb: KnowledgeBase, g: nx.Graph, cfg: AppConfig
) -> None:
    out = present(kb, g, cfg, handover_response(kb, "urgent", "urgent", 1.0))
    assert out["maps"] and "place-health_centre" in out["maps"][-1]["svg"]


def test_qr_svg_is_svg() -> None:
    svg = qr_svg("tel:+918040129100")
    assert "<svg" in svg and "</svg>" in svg and "<?xml" not in svg
