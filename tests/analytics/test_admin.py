from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from reception.config import load_config
from reception.dialogue.router import Assistant
from reception.engines.navigation import build_graph
from reception.kb.loader import KnowledgeBase, KnowledgeError
from reception.llm.base import FakeLLM
from reception.server.app import create_app

PIN = {"X-Admin-Pin": "2027"}


@pytest.fixture()
def client(kb: KnowledgeBase, classifier, index, tmp_path: Path):  # type: ignore[no-untyped-def]
    cfg = load_config(Path("configs/app.yaml"))
    cfg.analytics.db_path = tmp_path / "a.db"
    assistant = Assistant(kb, cfg, classifier, index, FakeLLM([]), build_graph(kb, cfg))
    calls = {"n": 0}

    def factory() -> Assistant:
        calls["n"] += 1
        if calls["n"] > 1:
            raise KnowledgeError("Knowledge base problems:\n- hours.yaml: invalid YAML")
        return assistant

    with TestClient(create_app(factory)) as c:
        yield c


def ask(c: TestClient, text: str) -> None:
    with c.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "ask", "text": text, "t": 1.0})
        for _ in range(10):
            if ws.receive_json()["type"] == "response":
                break


def test_admin_requires_pin(client: TestClient) -> None:
    assert client.get("/api/admin/summary").status_code == 401
    assert client.get("/api/admin/summary", headers={"X-Admin-Pin": "nope"}).status_code == 401


def test_turns_are_logged(client: TestClient) -> None:
    ask(client, "where is the xerox shop")
    ask(client, "my phone is 9845012345")
    s = client.get("/api/admin/summary", headers=PIN).json()
    assert s["turns"] == 2 and s["top_locations"][0]["place_id"] == "xerox_shop"
    csv_text = client.get("/api/admin/export.csv", headers=PIN).text
    assert "9845012345" not in csv_text and "[phone]" in csv_text


def test_sessions_closed_on_disconnect(client: TestClient) -> None:
    ask(client, "hello")
    s = client.get("/api/admin/summary", headers=PIN).json()
    assert s["sessions"] == 1


def test_reload_failure_keeps_old_knowledge(client: TestClient) -> None:
    r = client.post("/api/admin/reload", headers=PIN)
    assert r.status_code == 400 and "hours.yaml" in r.json()["errors"]
    assert client.get("/api/health").json()["ok"] is True


def test_admin_page_served(client: TestClient) -> None:
    assert "Dashboard" in client.get("/admin").text
