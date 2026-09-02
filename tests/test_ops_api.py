"""
@file        tests/test_ops_api.py
@purpose     The editor's write door behaves: every op lands through core.ops
             with canonical files, stale digests answer 409 while fresh ones
             pass, positions and container collapse go to view.yaml only
             (sorted, flow-style, the latter's key dropped when empty),
             errors keep their messages at 400, and the braid endpoint
             compiles.
@layer       tests
@tags        ops-envelope, digests, conflicts, view-layout
@related     kumihimo/server/ops_api.py (under test),
             kumihimo/server/app.py (the routes)
@design      PLAN.md §5.2-5.3, roadmap items editor-ops and editor-conflicts
"""

from pathlib import Path

from fastapi.testclient import TestClient

from kumihimo import Plan
from kumihimo.server.app import build_app
from tests.conftest import PlanFactory

BODIED = "---\nkind: task\n---\nBody.\n"


def client_for(root: Path, tmp_path: Path) -> TestClient:
    return TestClient(build_app(root, static_dir=tmp_path / "static-none"))


def digest_of(client: TestClient, node_id: str) -> str:
    payload = client.get("/api/plan").json()
    node = next(n for n in payload["nodes"] if n["id"] == node_id)
    return str(node["digest"])


def test_full_editor_session_through_the_api(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"seed.md": BODIED})
    client = client_for(root, tmp_path)

    assert (
        client.post(
            "/api/ops", json={"op": "add_node", "node_id": "one", "kind": "task", "body": "One.\n"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/ops",
            json={
                "op": "add_node",
                "node_id": "two",
                "kind": "task",
                "body": "Two.\n",
                "needs": ["one"],
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/ops", json={"op": "link", "src": "two", "to": "seed", "rel": "informs"}
        ).status_code
        == 200
    )
    digest = digest_of(client, "one")
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "one",
            "base_digest": digest,
            "set_fields": {"effort": "M"},
            "title": "Node one",
        },
    )
    assert response.status_code == 200
    assert (
        client.post(
            "/api/ops", json={"op": "rename_node", "old": "seed", "new": "kernel"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/ops",
            json={
                "op": "set_positions",
                "positions": {"one": {"x": 10, "y": 20}, "two": {"x": 200, "y": 20}},
            },
        ).status_code
        == 200
    )

    plan = Plan.load(root)
    assert plan.nodes["one"].fields["effort"] == "M"
    assert plan.nodes["two"].needs == ["one"]
    assert plan.nodes["two"].links[0].to == "kernel"
    assert (root / "nodes" / "one.md").read_text(encoding="utf-8") == (
        "---\nkind: task\ntitle: Node one\neffort: M\n---\nOne.\n"
    )
    view = (root / "view.yaml").read_text(encoding="utf-8")
    assert "one: {x: 10, y: 20}" in view
    assert plan.check() == []


def test_stale_digest_answers_409_and_changes_nothing(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    client = client_for(root, tmp_path)
    stale = digest_of(client, "a")
    # Someone else edits the file after our snapshot.
    target = root / "nodes" / "a.md"
    target.write_bytes(target.read_bytes().replace(b"effort: S", b"effort: L"))
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": stale,
            "set_fields": {"effort": "M"},
        },
    )
    assert response.status_code == 409
    assert "changed since" in response.json()["detail"]
    assert b"effort: L" in target.read_bytes()  # the concurrent edit survived


def test_fresh_digest_passes(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            "title": "Fresh",
        },
    )
    assert response.status_code == 200
    assert Plan.load(root).nodes["a"].title == "Fresh"


def test_op_errors_keep_their_messages_at_400(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir(
        {"a.md": "---\nkind: task\nneeds: [b]\n---\nA.\n", "b.md": BODIED.replace("Body", "B")}
    )
    client = client_for(root, tmp_path)
    response = client.post("/api/ops", json={"op": "link", "src": "b", "needs": "a"})
    assert response.status_code == 400
    assert "closes a cycle" in response.json()["detail"]
    unknown = client.post("/api/ops", json={"op": "add_node", "node_id": "x", "kind": "alien"})
    assert unknown.status_code == 400
    assert "unknown kind" in unknown.json()["detail"]


def test_unknown_op_shape_is_422(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    assert client.post("/api/ops", json={"op": "explode"}).status_code == 422
    assert (
        client.post(
            "/api/ops", json={"op": "add_node", "node_id": "y", "kind": "task", "surprise": 1}
        ).status_code
        == 422
    )


def test_braid_endpoint_compiles_and_slices(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip.\n",
            "a.md": "---\nkind: task\nin: [m]\n---\nA.\n",
            "b.md": "---\nkind: task\nin: [m]\nneeds: [a]\n---\nB.\n",
        }
    )
    client = client_for(root, tmp_path)
    text = client.get("/api/braid").text
    assert text.startswith("# Braid: Fixture")
    dry = client.get("/api/braid", params={"dry": "true", "in_group": "m"}).text
    assert dry.startswith("braid order")
    assert client.get("/api/braid", params={"strategy": "spiral"}).status_code == 400


def test_dirty_endpoint_reports_untracked_gracefully(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    body = client.get("/api/dirty").json()
    assert body["tracked"] in (True, False)
    assert isinstance(body["dirty"], list)


def test_link_and_unlink_mention_edges(plan_dir: PlanFactory, tmp_path: Path) -> None:
    # Trigger: agents=/skills=/trains= round-trip through link then unlink,
    # same as needs=/in_=/to= already do above.
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nWright.\n",
            "iteration.md": "---\nkind: skill\n---\nIteration.\n",
            "a.md": BODIED,
        }
    )
    client = client_for(root, tmp_path)
    for key, target in (("agents", "wright"), ("skills", "iteration"), ("trains", "wright")):
        response = client.post("/api/ops", json={"op": "link", "src": "a", key: target})
        assert response.status_code == 200
    plan = Plan.load(root)
    assert plan.nodes["a"].agents == ["wright"]
    assert plan.nodes["a"].skills == ["iteration"]
    assert plan.nodes["a"].trains == ["wright"]

    assert (
        client.post("/api/ops", json={"op": "unlink", "src": "a", "agents": "wright"}).status_code
        == 200
    )
    assert Plan.load(root).nodes["a"].agents == []


def test_link_mention_wrong_kind_is_400(plan_dir: PlanFactory, tmp_path: Path) -> None:
    # Non-trigger for the kind rule: "b" exists but isn't kind agent.
    root = plan_dir({"a.md": BODIED, "b.md": BODIED.replace("Body", "B")})
    client = client_for(root, tmp_path)
    response = client.post("/api/ops", json={"op": "link", "src": "a", "agents": "b"})
    assert response.status_code == 400
    assert "'agents' target 'b' is kind task, expected agent" in response.json()["detail"]


def test_link_mention_dangling_target_is_400(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    response = client.post("/api/ops", json={"op": "link", "src": "a", "skills": "ghost"})
    assert response.status_code == 400
    assert "edge target 'ghost' does not exist" in response.json()["detail"]


def test_link_two_mention_kwargs_is_400(plan_dir: PlanFactory, tmp_path: Path) -> None:
    # The envelope carries all six optionally; core.ops still enforces
    # exactly one of them.
    root = plan_dir({"a.md": BODIED, "wright.md": "---\nkind: agent\n---\nW.\n"})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops", json={"op": "link", "src": "a", "agents": "wright", "trains": "wright"}
    )
    assert response.status_code == 400
    assert "exactly one of" in response.json()["detail"]


def test_set_collapsed_persists_and_drops_the_key_when_empty(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip.\n",
            "a.md": "---\nkind: task\nin: [m]\n---\nA.\n",
        }
    )
    client = client_for(root, tmp_path)

    collapse = client.post("/api/ops", json={"op": "set_collapsed", "collapsed": ["m"]})
    assert collapse.status_code == 200
    assert collapse.json()["collapsed"] == ["m"]
    view = (root / "view.yaml").read_text(encoding="utf-8")
    assert "collapsed: [m]" in view

    uncollapse = client.post("/api/ops", json={"op": "set_collapsed", "collapsed": []})
    assert uncollapse.status_code == 200
    assert uncollapse.json()["collapsed"] == []
    view_after = (root / "view.yaml").read_text(encoding="utf-8")
    assert "collapsed" not in view_after


def test_set_collapsed_rejects_an_unknown_id(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip.\n",
            "a.md": "---\nkind: task\nin: [m]\n---\nA.\n",
        }
    )
    client = client_for(root, tmp_path)
    response = client.post("/api/ops", json={"op": "set_collapsed", "collapsed": ["ghost"]})
    assert response.status_code == 400
    assert "no node 'ghost'" in response.json()["detail"]
    assert not (root / "view.yaml").is_file()  # rejected before any write


def test_set_collapsed_rejects_a_node_that_is_not_a_container(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip.\n",
            "a.md": "---\nkind: task\nin: [m]\n---\nA.\n",
        }
    )
    client = client_for(root, tmp_path)
    # "a" is a real node but nothing names it in `in` — it has no members.
    response = client.post("/api/ops", json={"op": "set_collapsed", "collapsed": ["a"]})
    assert response.status_code == 400
    assert "'a' is not a container" in response.json()["detail"]
    assert not (root / "view.yaml").is_file()
