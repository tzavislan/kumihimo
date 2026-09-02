"""
@file        tests/test_server.py
@purpose     The watching server behaves: the payload carries the canvas
             contract, the WebSocket sends the initial state and then whatever
             the broadcaster publishes, the unbuilt-frontend fallback is honest,
             and the watch filter ignores exactly the churn it should.
@layer       tests
@tags        server, payload, websocket, watch-filter
@related     kumihimo/server/app.py (under test),
             kumihimo/server/watch.py (filter + broadcaster under test)
@design      PLAN.md §5.2, roadmap item server-watch
"""

from pathlib import Path

from fastapi.testclient import TestClient

from kumihimo.server.app import build_app
from kumihimo.server.payload import plan_payload
from kumihimo.server.watch import is_relevant
from tests.conftest import PlanFactory

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "apiguard"


def test_payload_carries_the_canvas_contract() -> None:
    payload = plan_payload(EXAMPLE)
    assert payload["plan"] == "API Guard"
    assert len(payload["nodes"]) == 7
    node = next(n for n in payload["nodes"] if n["id"] == "rate-limit-core")
    assert node["effective"]["status"] == "todo"
    assert "status" not in node["fields"]
    assert node["links"] == [{"to": "redis-outage", "rel": "threatened-by"}]
    assert payload["layout"]["api-endpoints"] == {"x": 40, "y": 200}
    assert payload["kinds"]["task"]["fields"]["effort"]["options"] == ["S", "M", "L"]
    assert payload["findings"] == []
    assert payload["collapsed"] == []  # no view.yaml `collapsed` key in this fixture


def test_payload_carries_mention_edges(plan_dir: PlanFactory) -> None:
    # Trigger: a node with all three mention keys populated. Non-trigger:
    # the agent node itself, which mentions nothing, gets the empty-list
    # default rather than a missing key.
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nWright.\n",
            "iteration.md": "---\nkind: skill\n---\nIteration.\n",
            "build.md": (
                "---\nkind: task\nagents: [wright]\nskills: [iteration]\n"
                "trains: [wright, iteration]\n---\nBuild.\n"
            ),
        }
    )
    payload = plan_payload(root)
    node = next(n for n in payload["nodes"] if n["id"] == "build")
    assert node["agents"] == ["wright"]
    assert node["skills"] == ["iteration"]
    assert node["trains"] == ["wright", "iteration"]
    agent = next(n for n in payload["nodes"] if n["id"] == "wright")
    assert agent["agents"] == []
    assert agent["skills"] == []
    assert agent["trains"] == []


def test_payload_filters_collapsed_against_live_node_ids(plan_dir: PlanFactory) -> None:
    # A view.yaml older than ops_api.py's set_collapsed validation (or hand-
    # edited) can still name a container that's since been renamed or
    # removed — the payload must drop it quietly rather than echo a phantom
    # collapsed id the canvas has no node for.
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip.\n",
            "a.md": "---\nkind: task\nin: [m]\n---\nA.\n",
        }
    )
    (root / "view.yaml").write_text("collapsed: [ghost, m]\n", encoding="utf-8")
    assert plan_payload(root)["collapsed"] == ["m"]


def test_api_plan_route_serves_the_payload(tmp_path: Path) -> None:
    client = TestClient(build_app(EXAMPLE, static_dir=tmp_path))
    response = client.get("/api/plan")
    assert response.status_code == 200
    assert response.json()["plan"] == "API Guard"


def test_unbuilt_frontend_fallback_is_honest(tmp_path: Path) -> None:
    client = TestClient(build_app(EXAMPLE, static_dir=tmp_path))
    response = client.get("/")
    assert response.status_code == 200
    assert "not built" in response.text
    assert "/api/plan" in response.text


def test_built_frontend_is_served_when_present(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_bytes(b"<!doctype html><title>canvas</title>ok")
    client = TestClient(build_app(EXAMPLE, static_dir=tmp_path))
    assert "canvas" in client.get("/").text


def test_websocket_sends_initial_then_published_payloads(tmp_path: Path) -> None:
    app = build_app(EXAMPLE, static_dir=tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/api/ws") as websocket:
        first = websocket.receive_json()
        assert first["plan"] == "API Guard"
        app.state.broadcaster.publish({"plan": "pushed", "nodes": []})
        second = websocket.receive_json()
        assert second["plan"] == "pushed"


def test_watch_filter_matches_plan_files_only() -> None:
    root = EXAMPLE
    assert is_relevant(root, str(root / "nodes" / "rate-limit-core.md"))
    assert is_relevant(root, str(root / "kumihimo.yaml"))
    assert is_relevant(root, str(root / "view.yaml"))
    assert not is_relevant(root, str(root / "nodes" / "draft.md.tmp"))
    assert not is_relevant(root, str(root / ".git" / "index"))
    assert not is_relevant(root, str(root.parent / "elsewhere.md"))
    assert not is_relevant(root, str(root / "notes.txt"))
