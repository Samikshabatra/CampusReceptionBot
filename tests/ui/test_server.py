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


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["ok"] is True and body["courses"] == 153


def test_index_page(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "Central Block" in r.text


def test_ask_over_ws(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "state"
        ws.send_json({"type": "ask", "text": "Where is the xerox shop?"})
        msg = ws.receive_json()
        while msg["type"] != "response":
            msg = ws.receive_json()
        assert [m["floor"] for m in msg["data"]["maps"]] == ["G", "B"]


def test_followup_keeps_context_until_new_session(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for text in ("MCA fees", "and for NRI?"):
            ws.send_json({"type": "ask", "text": text})
            msg = ws.receive_json()
            while msg["type"] != "response":
                msg = ws.receive_json()
        assert "NRI" in msg["data"]["speech"]
        assert ws.receive_json() == {"type": "state", "state": "listening"}
        ws.send_json({"type": "new_session"})
        assert ws.receive_json() == {"type": "state", "state": "idle"}


def test_malformed_message_keeps_connection(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_text("not json")
        assert ws.receive_json()["type"] == "error"
        ws.send_json({"type": "ask", "text": "hello"})
        msg = ws.receive_json()
        while msg["type"] != "response":
            msg = ws.receive_json()
        assert msg["data"]["intent"] == "greeting"


def test_reconnect_after_disconnect(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "state"


def test_page_and_scripts_are_revalidated(client: TestClient) -> None:
    for path in ("/", "/static/app.js", "/static/app.css", "/static/av.js"):
        r = client.get(path)
        assert r.status_code == 200 and "no-cache" in r.headers.get("cache-control", ""), path
