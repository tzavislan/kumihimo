"""
@file        tests/test_ops_api.py
@purpose     The editor's write door behaves: every op lands through core.ops
             with canonical files, stale digests answer 409 while fresh ones
             pass, positions and container collapse go to view.yaml only
             (sorted, flow-style, the latter's key dropped when empty),
             errors keep their messages at 400, the braid endpoint compiles,
             /api/dirty gates tracked=true on the enclosing repo actually
             tracking at least one file under the plan root rather than
             merely enclosing it (K37), and (K32) every op response carries
             a correctly-shaped inverse envelope, digest preconditions that
             go stale after an external edit, byte-exact round-trips
             (including through a referrer-fixing rename), and undo-of-undo.
             (K45) remove_node's inverse is a restore_node envelope carrying
             the exact prior bytes and position, postable straight back;
             restore_node's own inverse is remove_node; a force-remove's
             stripped referrers stay stripped through a restore; restoring
             onto a still-live id is a clean 400.
@layer       tests
@tags        ops-envelope, digests, conflicts, view-layout, undo, inverse-ops,
             dirty, git, restore
@related     kumihimo/server/ops_api.py (under test),
             kumihimo/server/app.py (the routes, incl. /api/dirty)
@design      PLAN.md §5.2-5.3, roadmap items editor-ops and editor-conflicts;
             PLAN2.md §2.5 Undo trail, §5 risk 4, queue items K32, K37, K45
"""

import subprocess
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


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_dirty_endpoint_false_when_enclosing_repo_does_not_track_the_plan(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    # Trigger (K37): tmp_path becomes a real git repo — exactly what happens
    # when a plan is scaffolded somewhere under the user's home directory,
    # which can itself be a repo root — but the plan is never `git add`-ed.
    # An enclosing .git must not be enough on its own: this used to answer
    # tracked=true with every scaffold file listed as eternally "??" dirty.
    root = plan_dir({"a.md": BODIED})
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=tmp_path)
    _git("config", "user.name", "Test", cwd=tmp_path)
    client = client_for(root, tmp_path)
    assert client.get("/api/dirty").json() == {"tracked": False, "dirty": []}


def test_dirty_endpoint_true_when_the_repo_tracks_the_plan(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    # Non-trigger: a scratch repo that genuinely tracks the plan (init, add,
    # commit) must still answer tracked=true and name a file dirtied after —
    # the K37 gate must not swallow the real case (plans/roadmap's own
    # indicator depends on exactly this path; not exercised here directly to
    # keep this test hermetic, per the builder's instruction not to mutate
    # it).
    root = plan_dir({"a.md": BODIED})
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=tmp_path)
    _git("config", "user.name", "Test", cwd=tmp_path)
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-q", "-m", "scaffold", cwd=tmp_path)
    (root / "nodes" / "a.md").write_text(BODIED.replace("Body", "Changed"), encoding="utf-8")

    client = client_for(root, tmp_path)
    body = client.get("/api/dirty").json()
    assert body["tracked"] is True
    assert any("a.md" in line for line in body["dirty"])


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


# --- K32: inverse-op undo trail ---------------------------------------------


def test_inverse_add_node_is_remove_without_force(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"seed.md": BODIED})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops", json={"op": "add_node", "node_id": "fresh", "kind": "task", "body": "New.\n"}
    )
    assert response.status_code == 200
    body = response.json()
    digest = digest_of(client, "fresh")
    assert body["inverse"] == {"op": "remove_node", "node_id": "fresh", "base_digest": digest}
    assert body["preconditions"] == [{"id": "fresh", "digest": digest}]
    assert body["label"] == "add fresh"

    undo = client.post("/api/ops", json=body["inverse"])
    assert undo.status_code == 200
    assert not (root / "nodes" / "fresh.md").exists()


def test_inverse_remove_node_is_restore_with_exact_content_and_position(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    # K45: remove_node's inverse used to be an honest None (git was the only
    # undo for a deletion, PLAN2.md §2.5) — it is now a restore_node envelope
    # carrying the exact prior bytes, read before the file was deleted, plus
    # the node's view.yaml position when it had one.
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    (root / "view.yaml").write_bytes(b"layout:\n  a: {x: 10, y: 20}\n")
    client = client_for(root, tmp_path)
    original = (root / "nodes" / "a.md").read_bytes()

    response = client.post(
        "/api/ops",
        json={"op": "remove_node", "node_id": "a", "base_digest": digest_of(client, "a")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inverse"] == {
        "op": "restore_node",
        "node_id": "a",
        "content": original.decode("utf-8"),
        "position": [10, 20],
    }
    # "This id is absent" can't be expressed as a {id, digest} precondition
    # against today's frontend trail matcher without a frontend edit this
    # round didn't make (see OpOutcome's own docstring) — empty means
    # always-enabled, the same honest fallback set_positions/set_collapsed
    # already use.
    assert body["preconditions"] == []
    assert body["label"] == "remove a"

    undo = client.post("/api/ops", json=body["inverse"])
    assert undo.status_code == 200
    assert (root / "nodes" / "a.md").read_bytes() == original
    assert "a: {x: 10, y: 20}" in (root / "view.yaml").read_text(encoding="utf-8")


def test_inverse_update_field_restores_prior_value_and_unsets_new_field(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            # effort already exists (S -> M, restorable); risk is brand new
            # (must unset back out, not restore to a fabricated value); title
            # resent unchanged must not appear in the inverse at all.
            "set_fields": {"effort": "M", "risk": "high"},
            "title": None,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inverse"]["set_fields"] == {"effort": "S"}
    assert body["inverse"]["unset_fields"] == ["risk"]
    assert "title" not in body["inverse"]
    assert "effort: S → M" in body["label"]
    assert "risk: (none) → high" in body["label"]


def test_inverse_update_resent_unchanged_field_produces_no_clause(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    # Trigger for the "resent unchanged" branch: NodeForm.tsx's Save resends
    # every visible field regardless of whether it actually changed.
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            "set_fields": {"effort": "S"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "set_fields" not in body["inverse"]
    assert "unset_fields" not in body["inverse"]
    assert body["label"] == "update a"


def test_inverse_update_body_restores_prior_body(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": "---\nkind: task\n---\nOld body.\n"})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            "body": "New body.\n",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["inverse"]["body"] == "Old body.\n"
    assert body["label"] == "update a: body edited"


def test_inverse_link_is_unlink_same_key(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": BODIED.replace("Body", "B")})
    client = client_for(root, tmp_path)
    response = client.post("/api/ops", json={"op": "link", "src": "a", "needs": "b"})
    assert response.status_code == 200
    body = response.json()
    digest = digest_of(client, "a")
    assert body["inverse"] == {"op": "unlink", "src": "a", "base_digest": digest, "needs": "b"}
    assert body["label"] == "link: a needs b"

    undo = client.post("/api/ops", json=body["inverse"])
    assert undo.status_code == 200
    assert Plan.load(root).nodes["a"].needs == []


def test_inverse_unlink_is_link_with_same_rel(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": BODIED.replace("Body", "B")})
    client = client_for(root, tmp_path)
    assert (
        client.post(
            "/api/ops", json={"op": "link", "src": "a", "to": "b", "rel": "threatens"}
        ).status_code
        == 200
    )
    response = client.post("/api/ops", json={"op": "unlink", "src": "a", "to": "b"})
    assert response.status_code == 200
    body = response.json()
    digest = digest_of(client, "a")
    assert body["inverse"] == {
        "op": "link",
        "src": "a",
        "base_digest": digest,
        "to": "b",
        "rel": "threatens",
    }
    assert body["label"] == "unlink: a links b (threatens)"

    undo = client.post("/api/ops", json=body["inverse"])
    assert undo.status_code == 200
    assert Plan.load(root).nodes["a"].links[0].rel == "threatens"


def test_inverse_rename_is_reverse_rename(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    response = client.post("/api/ops", json={"op": "rename_node", "old": "a", "new": "b"})
    assert response.status_code == 200
    body = response.json()
    digest = digest_of(client, "b")
    assert body["inverse"] == {"op": "rename_node", "old": "b", "new": "a", "base_digest": digest}
    assert body["label"] == "rename a → b"


def test_inverse_set_positions_restores_prior_and_omits_first_placement(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    first = client.post(
        "/api/ops", json={"op": "set_positions", "positions": {"a": {"x": 10, "y": 20}}}
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["inverse"] is None  # no prior explicit position to restore
    assert first_body["preconditions"] == []
    assert first_body["label"] == "move a"

    second = client.post(
        "/api/ops", json={"op": "set_positions", "positions": {"a": {"x": 99, "y": 99}}}
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["inverse"] == {
        "op": "set_positions",
        "positions": {"a": {"x": 10, "y": 20}},
    }

    undo = client.post("/api/ops", json=second_body["inverse"])
    assert undo.status_code == 200
    view = (root / "view.yaml").read_text(encoding="utf-8")
    assert "a: {x: 10, y: 20}" in view


def test_inverse_set_collapsed_restores_prior(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip.\n",
            "a.md": "---\nkind: task\nin: [m]\n---\nA.\n",
        }
    )
    client = client_for(root, tmp_path)
    collapse = client.post("/api/ops", json={"op": "set_collapsed", "collapsed": ["m"]})
    assert collapse.status_code == 200
    collapse_body = collapse.json()
    assert collapse_body["inverse"] == {"op": "set_collapsed", "collapsed": []}
    assert collapse_body["preconditions"] == []
    assert collapse_body["label"] == "collapse m"

    expand = client.post("/api/ops", json=collapse_body["inverse"])
    assert expand.status_code == 200
    expand_body = expand.json()
    assert expand_body["inverse"] == {"op": "set_collapsed", "collapsed": ["m"]}
    assert expand_body["label"] == "expand m"


def test_precondition_digest_goes_stale_after_external_edit(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            "set_fields": {"effort": "M"},
        },
    )
    assert response.status_code == 200
    precondition = response.json()["preconditions"][0]
    assert precondition == {"id": "a", "digest": digest_of(client, "a")}

    # A second op, "B", touching the same node from entirely outside this
    # API — a CLI/MCP mutation or a hand edit, same as the existing
    # stale-digest test above simulates.
    target = root / "nodes" / "a.md"
    target.write_bytes(target.read_bytes().replace(b"effort: M", b"effort: L"))

    assert digest_of(client, "a") != precondition["digest"]


def test_inverse_round_trip_is_byte_identical(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    client = client_for(root, tmp_path)
    target = root / "nodes" / "a.md"
    original = target.read_bytes()

    response = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            "set_fields": {"effort": "L"},
        },
    )
    assert response.status_code == 200
    assert target.read_bytes() != original  # the forward op did change the file

    undo = client.post("/api/ops", json=response.json()["inverse"])
    assert undo.status_code == 200
    assert target.read_bytes() == original


def test_rename_inverse_refixes_referrers_byte_for_byte(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir({"b.md": BODIED, "a.md": "---\nkind: task\nneeds: [b]\n---\nA.\n"})
    client = client_for(root, tmp_path)
    a_path = root / "nodes" / "a.md"
    original_a = a_path.read_bytes()
    original_b = (root / "nodes" / "b.md").read_bytes()

    response = client.post("/api/ops", json={"op": "rename_node", "old": "b", "new": "kernel"})
    assert response.status_code == 200
    inverse = response.json()["inverse"]
    assert inverse == {
        "op": "rename_node",
        "old": "kernel",
        "new": "b",
        "base_digest": digest_of(client, "kernel"),
    }
    assert a_path.read_text(encoding="utf-8") == "---\nkind: task\nneeds: [kernel]\n---\nA.\n"

    undo = client.post("/api/ops", json=inverse)
    assert undo.status_code == 200
    assert not (root / "nodes" / "kernel.md").exists()
    assert a_path.read_bytes() == original_a
    assert (root / "nodes" / "b.md").read_bytes() == original_b


def test_undo_of_undo_restores_forward_state(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": "---\nkind: task\neffort: S\n---\nBody.\n"})
    client = client_for(root, tmp_path)
    target = root / "nodes" / "a.md"

    forward = client.post(
        "/api/ops",
        json={
            "op": "update_node",
            "node_id": "a",
            "base_digest": digest_of(client, "a"),
            "set_fields": {"effort": "L"},
        },
    )
    assert forward.status_code == 200
    after_forward = target.read_bytes()

    undo = client.post("/api/ops", json=forward.json()["inverse"])
    assert undo.status_code == 200
    assert undo.json()["inverse"] is not None  # the undo op is itself undoable
    assert target.read_bytes() != after_forward

    redo = client.post("/api/ops", json=undo.json()["inverse"])
    assert redo.status_code == 200
    assert target.read_bytes() == after_forward


# --- K45: restore_node, remove's real inverse ------------------------------


def test_inverse_restore_node_is_remove_without_force(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    original = (root / "nodes" / "a.md").read_bytes()

    remove = client.post(
        "/api/ops",
        json={"op": "remove_node", "node_id": "a", "base_digest": digest_of(client, "a")},
    )
    assert remove.status_code == 200
    restore_inverse = remove.json()["inverse"]

    restore = client.post("/api/ops", json=restore_inverse)
    assert restore.status_code == 200
    restore_body = restore.json()
    digest = digest_of(client, "a")
    assert restore_body["inverse"] == {"op": "remove_node", "node_id": "a", "base_digest": digest}
    assert restore_body["preconditions"] == [{"id": "a", "digest": digest}]
    assert restore_body["label"] == "restore a"
    assert (root / "nodes" / "a.md").read_bytes() == original

    # Undo-of-undo-of-undo: re-removing through the restore's own inverse
    # works, completing the full add-like/remove-like cycle.
    re_remove = client.post("/api/ops", json=restore_body["inverse"])
    assert re_remove.status_code == 200
    assert not (root / "nodes" / "a.md").exists()


def test_restore_after_force_remove_does_not_resurrect_referrers(
    plan_dir: PlanFactory, tmp_path: Path
) -> None:
    root = plan_dir(
        {"target.md": BODIED, "dep.md": "---\nkind: task\nneeds: [target]\n---\nDep.\n"}
    )
    client = client_for(root, tmp_path)
    dep_before = (root / "nodes" / "dep.md").read_bytes()

    response = client.post(
        "/api/ops",
        json={
            "op": "remove_node",
            "node_id": "target",
            "base_digest": digest_of(client, "target"),
            "force": True,
        },
    )
    assert response.status_code == 200
    dep_after_strip = (root / "nodes" / "dep.md").read_bytes()
    assert dep_after_strip != dep_before  # the referrer edge really was stripped
    assert Plan.load(root).nodes["dep"].needs == []

    undo = client.post("/api/ops", json=response.json()["inverse"])
    assert undo.status_code == 200
    assert (root / "nodes" / "target.md").is_file()
    # The label/docs promise: restore returns the node file only.
    assert (root / "nodes" / "dep.md").read_bytes() == dep_after_strip
    assert Plan.load(root).nodes["dep"].needs == []


def test_restore_onto_an_existing_id_is_400(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = client_for(root, tmp_path)
    response = client.post(
        "/api/ops", json={"op": "restore_node", "node_id": "a", "content": BODIED}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
    # Refused, not clobbered.
    assert (root / "nodes" / "a.md").read_bytes() == BODIED.encode("utf-8")
