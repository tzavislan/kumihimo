"""
@file        tests/test_server.py
@purpose     The watching server behaves: the payload carries the canvas
             contract, the WebSocket sends the initial state and then whatever
             the broadcaster publishes, the unbuilt-frontend fallback is honest,
             the watch filter ignores exactly the churn it should, and (K31)
             EventTail starts at end-of-file and hands back only what's new.
@layer       tests
@tags        server, payload, websocket, watch-filter, events, attribution
@related     kumihimo/server/app.py (under test),
             kumihimo/server/watch.py (filter + broadcaster under test),
             kumihimo/server/events.py (EventTail under test)
@design      PLAN.md §5.2, roadmap item server-watch; PLAN2.md §2.5 Motion &
             attribution, queue item K31
"""

from pathlib import Path

from fastapi.testclient import TestClient

from kumihimo.core import ops, store
from kumihimo.server.app import build_app
from kumihimo.server.events import EventTail
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
    # events.jsonl itself never matches — its own writes must not trigger a
    # rebuild independent of whatever node/manifest change caused them (K31).
    assert not is_relevant(root, str(root / ".kumihimo" / "events.jsonl"))


def test_event_tail_starts_at_eof_and_hands_back_only_whats_new(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": "---\nkind: task\n---\nA.\n"})
    ops.add_node(root, "before", "task", actor="cli")  # written before the tail exists

    tail = EventTail(root)
    assert tail.read_new() == []  # history from before this tail started is not "new"

    ops.add_node(root, "after", "task", actor="mcp")
    assert tail.read_new() == [{"actor": "mcp", "op": "add_node", "targets": ["after"]}]
    assert tail.read_new() == []  # already-read events aren't handed back twice

    ops.link(root, "after", needs="before", actor="mcp")
    assert tail.read_new() == [{"actor": "mcp", "op": "link", "targets": ["after"]}]


def test_event_tail_survives_a_shrunk_file(plan_dir: PlanFactory) -> None:
    # Simulates the writer's own truncation landing between two reads: the
    # remembered offset would otherwise point past the new, smaller
    # end-of-file. Best-effort (kumihimo/server/events.py's own docstring):
    # this must not raise, even though the specific line it resets to isn't
    # guaranteed to be one it hasn't shown before (nothing was shipped yet
    # in this scenario, so the dedup memory below has nothing to filter).
    root = plan_dir({"a.md": "---\nkind: task\n---\nA.\n"})
    events_dir = root / store.EVENTS_DIR
    events_dir.mkdir()
    path = events_dir / store.EVENTS_FILE
    path.write_text(
        '{"actor": "cli", "op": "add_node", "targets": ["a", "b", "c"]}\n' * 20, encoding="utf-8"
    )
    tail = EventTail(root)
    path.write_text('{"actor": "mcp", "op": "add_node", "targets": ["z"]}\n', encoding="utf-8")
    assert tail.read_new() == [{"actor": "mcp", "op": "add_node", "targets": ["z"]}]


def test_event_tail_sustained_truncation_never_replays(tmp_path: Path) -> None:
    # Fix round: the original tight 200-line cap truncated on EVERY append
    # once past it, and a shorter new line evicting a longer old one shrinks
    # the file below EventTail's remembered offset — checker measured 40/40
    # consecutive full-log replays under exactly that steady-state pattern,
    # and a stale replayed event can misattribute a genuinely-changing
    # node's toast (attributionDiff.ts's first-claim-wins). Drives real
    # appends (through core.ops._log_event directly — the same reasoning
    # tests/test_events.py's own truncation test gives for skipping
    # ops.add_node's much slower per-call Plan.load) well past several
    # truncation cycles (ops.py's EVENTS_TRUNCATE_AT/EVENTS_KEEP hysteresis)
    # and asserts every single read_new() call returns EXACTLY the one
    # event just appended — never zero (a false-negative drop from the
    # dedup memory) and never more than one (a replay).
    from kumihimo.core.ops import _log_event

    root = tmp_path / "plan"
    root.mkdir()
    tail = EventTail(root)
    for i in range(3 * store.EVENTS_TRUNCATE_AT):
        target = f"n{i}"
        _log_event(root, "cli", "add_node", [target])
        assert tail.read_new() == [{"actor": "cli", "op": "add_node", "targets": [target]}]


def test_event_tail_on_a_plan_with_no_log_yet_is_empty_not_an_error(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": "---\nkind: task\n---\nA.\n"})
    assert EventTail(root).read_new() == []
