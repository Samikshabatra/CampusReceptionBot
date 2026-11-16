import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from reception.config import load_config
from reception.dialogue.router import Assistant
from reception.engines.navigation import build_graph
from reception.kb.loader import KnowledgeBase
from reception.llm.base import FakeLLM
from reception.server.app import create_app


@pytest.fixture(scope="module")
def client(kb: KnowledgeBase, classifier, index):  # type: ignore[no-untyped-def]
    cfg = load_config(Path("configs/app.yaml"))
    cfg.analytics.db_path = Path(tempfile.mkdtemp()) / "analytics.db"
    assistant = Assistant(kb, cfg, classifier, index, FakeLLM([]), build_graph(kb, cfg))
    with TestClient(create_app(lambda: assistant)) as c:
        yield c


def test_floor_svg(client: TestClient) -> None:
    r = client.get("/api/floor/B.svg", params={"highlight": "xerox_shop"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert 'id="place-xerox_shop" class="cell cat-shop hl"' in r.text
    assert client.get("/api/floor/Z.svg").status_code == 404


def test_places_lists_named_places(client: TestClient) -> None:
    places = client.get("/api/places").json()
    ids = {p["id"] for p in places}
    assert "xerox_shop" in ids and "library" in ids
    assert "8_fw_1" not in ids and "law_box_9" not in ids and "room_808" not in ids
    assert {"id", "name", "floor", "floor_name", "category"} <= set(places[0])


def test_departments(client: TestClient) -> None:
    deps = {d["name"]: d for d in client.get("/api/departments").json()}
    cs = deps["Department of Computer Science"]
    assert cs["count"] == 9 and cs["floor_name"] == "8th floor" and cs["floor"] == "8"
    assert deps["Department of Commerce"]["floor_name"] is None


def test_courses_filter(client: TestClient) -> None:
    dept = "Department of Computer Science"
    assert len(client.get("/api/courses", params={"department": dept}).json()) == 9
    assert len(client.get("/api/courses", params={"department": dept, "level": "PG"}).json()) == 4


def test_course_detail(client: TestClient) -> None:
    body = client.get("/api/course/50").json()
    assert body["course"]["name"] == "Master of Computer Applications (MCA)"
    assert body["fees"]["years"]["1"]["Karnataka"] == "2,42,000 INR"
    assert body["qr"][0]["svg"].startswith("<svg")
    assert client.get("/api/course/99999").status_code == 404


def test_calendar_month(client: TestClient) -> None:
    body = client.get("/api/calendar", params={"year": 2026, "month": 11}).json()
    names = {e["name"] for e in body["events"]}
    assert "Daksh & Open Day" in names
    assert any(h["date"] == "2026-11-10" for h in body["holidays"])
    assert body["month_name"] == "November 2026"


def test_contacts(client: TestClient) -> None:
    items = client.get("/api/contacts").json()
    assert {c["id"] for c in items} >= {
        "support_1",
        "admissions_1",
        "email_general",
        "library_site",
    }
    first = items[0]
    assert first["href"].startswith(("tel:", "mailto:", "https://")) and first["qr"].startswith(
        "<svg"
    )


def test_courses_without_department_lists_everything(client: TestClient) -> None:
    items = client.get("/api/courses").json()
    assert len(items) == 153 and all("department" in c for c in items)
    assert len(client.get("/api/courses", params={"level": "PhD"}).json()) == 29


def test_all_programmes_question_has_no_department(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json(
            {
                "type": "ask",
                "text": "Can you list all the programs offered by Christ University Central Campus?",
                "t": 1.0,
            }
        )
        msg = ws.receive_json()
        while msg["type"] != "response":
            msg = ws.receive_json()
        data = msg["data"]["card"]["data"]
        assert msg["data"]["card"]["kind"] == "course_list"
        assert data["department"] is None and len(data["items"]) == 153
