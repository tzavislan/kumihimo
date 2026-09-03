"""
@file        tests/test_events.py
@purpose     K31's advisory event log end to end: every mutating op appends
             `{actor, op, targets}` with the right actor per thin client (CLI
             "cli", MCP "mcp", the editor's ops API "editor", a raw library
             call's default "api"), every op works with a str root too (fix
             round: 5 of 6 logged the raw, possibly-str root instead of
             Plan.load's own resolved plan.root, raising TypeError from
             `str / str` after the mutation had already landed), rename/
             remove log every id a payload digest diff would actually see
             change, the log truncates to its last 200 lines (not its
             first), a write failure there never fails the op it's attached
             to, scaffold gitignores the log dir for new plans and a fresh
             scaffold plus an op stays invisible to `git status`, and the
             log's mere presence never perturbs check or braid output.
@layer       tests
@tags        events, attribution, advisory, actor, gitignore
@related     kumihimo/core/ops.py (_log_event, under test),
             kumihimo/core/store.py (EVENTS_DIR/EVENTS_FILE, scaffold's
             gitignore write), kumihimo/server/events.py (the tailer —
             covered by tests/test_server.py's own watch/payload tests)
@design      PLAN2.md §2.5 Motion & attribution, queue item K31
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from kumihimo import Plan
from kumihimo.cli.app import app
from kumihimo.core import ops, store
from kumihimo.core.errors import KumihimoError
from kumihimo.mcp import tools
from kumihimo.server.app import build_app
from tests.conftest import PlanFactory

BODIED = "---\nkind: task\n---\nBody.\n"
runner = CliRunner()


def read_events(root: Path) -> list[dict[str, Any]]:
    """Every line of this plan's events.jsonl, parsed, in file order."""
    path = root / store.EVENTS_DIR / store.EVENTS_FILE
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_default_actor_is_api_for_a_raw_library_call(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    ops.add_node(root, "b", "task")
    assert read_events(root) == [{"actor": "api", "op": "add_node", "targets": ["b"]}]


def test_all_mutating_ops_accept_a_str_root(plan_dir: PlanFactory) -> None:
    # Regression: add_node already logged plan.root (Plan.load's own
    # resolved Path), but the other five ops logged the raw `root`
    # parameter — fine for the Path every real client passes, but a str
    # (Plan.load itself accepts str | Path, so this is a documented, legal
    # call shape for a raw "api" library caller) hit `str / str` inside
    # _log_event, raised TypeError, and propagated past the helper's own
    # `except OSError` — after the mutation had already landed on disk, so
    # the caller saw a crash for a write that actually succeeded. Runs every
    # mutating op, once each, with a str root end to end.
    root = plan_dir({"a.md": BODIED, "ref.md": "---\nkind: task\nneeds: [a]\n---\nRef.\n"})
    str_root = str(root)

    ops.add_node(str_root, "c", "task", actor="cli")
    ops.update_node(str_root, "c", set_fields={"effort": "M"}, actor="cli")
    ops.link(str_root, "c", needs="a", actor="cli")
    ops.unlink(str_root, "c", needs="a", actor="cli")
    ops.rename_node(str_root, "c", "d", actor="cli")
    ops.remove_node(str_root, "d", actor="cli")

    events = read_events(root)
    assert [event["op"] for event in events] == [
        "add_node",
        "update_node",
        "link",
        "unlink",
        "rename_node",
        "remove_node",
    ]
    assert all(event["actor"] == "cli" for event in events)


def test_cli_add_logs_actor_cli(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    runner.invoke(app, ["new", plan], env={"COLUMNS": "250"})
    result = runner.invoke(
        app, ["add", plan, "b", "--kind", "task", "--body", "B."], env={"COLUMNS": "250"}
    )
    assert result.exit_code == 0
    events = read_events(Path(plan))
    assert {"actor": "cli", "op": "add_node", "targets": ["b"]} in events


def test_cli_link_and_set_also_log_actor_cli(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    env = {"COLUMNS": "250"}
    runner.invoke(app, ["new", plan], env=env)
    runner.invoke(app, ["add", plan, "b", "--kind", "task", "--body", "B."], env=env)
    runner.invoke(app, ["link", plan, "b", "--to", "first-thread"], env=env)
    runner.invoke(app, ["set", plan, "b", "--title", "Titled"], env=env)
    events = read_events(Path(plan))
    ops_and_actors = [(e["op"], e["actor"]) for e in events]
    assert ("link", "cli") in ops_and_actors
    assert ("update_node", "cli") in ops_and_actors


def test_mcp_add_logs_actor_mcp(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    tools.add_node(root, "b", "task", body="B.")
    assert read_events(root) == [{"actor": "mcp", "op": "add_node", "targets": ["b"]}]


def test_mcp_update_link_unlink_rename_remove_log_actor_mcp(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": BODIED})
    tools.update_node(root, "b", set_fields={"effort": "M"})
    tools.link(root, "b", needs="a")
    tools.unlink(root, "b", needs="a")
    tools.rename_node(root, "b", "c")
    tools.remove_node(root, "c")
    actors = {e["actor"] for e in read_events(root)}
    assert actors == {"mcp"}
    ops_seen = [e["op"] for e in read_events(root)]
    assert ops_seen == ["update_node", "link", "unlink", "rename_node", "remove_node"]


def test_ops_api_add_logs_actor_editor(plan_dir: PlanFactory, tmp_path: Path) -> None:
    root = plan_dir({"a.md": BODIED})
    client = TestClient(build_app(root, static_dir=tmp_path / "static-none"))
    response = client.post(
        "/api/ops", json={"op": "add_node", "node_id": "b", "kind": "task", "body": "B.\n"}
    )
    assert response.status_code == 200
    assert read_events(root) == [{"actor": "editor", "op": "add_node", "targets": ["b"]}]


def test_link_and_unlink_log_the_source_only(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": BODIED})
    ops.link(root, "b", needs="a", actor="cli")
    ops.unlink(root, "b", needs="a", actor="cli")
    assert read_events(root) == [
        {"actor": "cli", "op": "link", "targets": ["b"]},
        {"actor": "cli", "op": "unlink", "targets": ["b"]},
    ]


def test_rename_logs_old_new_and_every_rewritten_referrer(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {"old-name.md": BODIED, "ref.md": "---\nkind: task\nneeds: [old-name]\n---\nRef.\n"}
    )
    ops.rename_node(root, "old-name", "new-name", actor="mcp")
    event = read_events(root)[-1]
    assert event["actor"] == "mcp"
    assert event["op"] == "rename_node"
    assert sorted(event["targets"]) == ["new-name", "old-name", "ref"]


def test_remove_with_force_logs_the_node_and_its_referrers(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {"target.md": BODIED, "ref.md": "---\nkind: task\nneeds: [target]\n---\nRef.\n"}
    )
    ops.remove_node(root, "target", force=True, actor="cli")
    event = read_events(root)[-1]
    assert event["op"] == "remove_node"
    assert sorted(event["targets"]) == ["ref", "target"]


def test_remove_without_referrers_logs_just_the_node(plan_dir: PlanFactory) -> None:
    root = plan_dir({"solo.md": BODIED})
    ops.remove_node(root, "solo", actor="cli")
    assert read_events(root) == [{"actor": "cli", "op": "remove_node", "targets": ["solo"]}]


def test_log_grows_past_200_then_truncates_to_the_newest_200_at_400(tmp_path: Path) -> None:
    # Fix round: truncation is hysteresis (store.EVENTS_KEEP/
    # EVENTS_TRUNCATE_AT), not a tight cap at 200 — the original tight cap
    # rewrote the file to the same ~200-line size on nearly every append
    # once past it, and EventTail's remembered offset shrinking below the
    # new file's size on nearly every one of those writes forced a full-log
    # replay far more often than truncation itself needed to run (fix 2).
    # Exercises core.ops._log_event directly rather than through 400+ real
    # ops.add_node calls: each of those reloads the whole (growing) plan
    # from disk, which turns this from a sub-second unit test into a
    # multi-minute one for no extra coverage — truncation is entirely this
    # one helper's own loop, verified live to behave the same either way
    # before choosing this shortcut.
    from kumihimo.core.ops import _log_event

    root = tmp_path / "plan"
    root.mkdir()
    for i in range(store.EVENTS_TRUNCATE_AT):
        _log_event(root, "cli", "add_node", [f"n{i}"])
    grown = read_events(root)
    assert len(grown) == store.EVENTS_TRUNCATE_AT  # no truncation yet, right at the ceiling
    assert [e["targets"][0] for e in grown] == [f"n{i}" for i in range(store.EVENTS_TRUNCATE_AT)]

    _log_event(root, "cli", "add_node", [f"n{store.EVENTS_TRUNCATE_AT}"])  # tips it over
    truncated = read_events(root)
    assert len(truncated) == store.EVENTS_KEEP
    # The tail survived, not the head — a bare length check alone couldn't
    # tell "keeps the newest EVENTS_KEEP" from "keeps some EVENTS_KEEP".
    first_kept = store.EVENTS_TRUNCATE_AT + 1 - store.EVENTS_KEEP
    assert [e["targets"][0] for e in truncated] == [
        f"n{i}" for i in range(first_kept, store.EVENTS_TRUNCATE_AT + 1)
    ]


def test_op_succeeds_when_the_events_dir_is_unwritable(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    # A plain file sits where the events directory would go: mkdir(parents=
    # True, exist_ok=True) still raises against a non-directory obstruction,
    # simulating "the advisory log can't be written" portably — no chmod/ACL
    # trick needed, and it behaves identically on Windows and POSIX.
    (root / store.EVENTS_DIR).write_bytes(b"not a directory")
    node = ops.add_node(root, "b", "task", actor="cli")
    assert node.id == "b"
    assert Plan.load(root).nodes["b"].id == "b"
    # The obstruction is untouched: _log_event swallowed the OSError rather
    # than raising, or somehow clearing the way for itself.
    assert (root / store.EVENTS_DIR).is_file()


def test_add_node_actor_still_rejects_other_add_errors(plan_dir: PlanFactory) -> None:
    # actor is purely advisory metadata — it must never relax add_node's
    # existing structural refusals (K31 must not become a second write door).
    root = plan_dir({"a.md": BODIED})
    with pytest.raises(KumihimoError, match="already exists"):
        ops.add_node(root, "a", "task", actor="cli")


def test_scaffold_gitignore_contains_the_events_dir(tmp_path: Path) -> None:
    root = store.scaffold(tmp_path / "demo")
    text = (root / ".gitignore").read_text(encoding="utf-8")
    assert f"{store.EVENTS_DIR}/" in text.splitlines()


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_fresh_scaffold_plus_op_keeps_git_status_clean_of_the_log(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    root = store.scaffold(repo / "plan", name="Demo")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "scaffold", cwd=repo)

    ops.add_node(root, "extra", "task", actor="cli")
    assert (root / store.EVENTS_DIR / store.EVENTS_FILE).is_file()

    status = _git("status", "--porcelain", cwd=repo).stdout
    assert ".kumihimo" not in status
    assert "events.jsonl" not in status
    assert "extra.md" in status  # the new node itself IS legitimately untracked


def test_check_and_braid_are_byte_identical_with_and_without_the_log(tmp_path: Path) -> None:
    root = store.scaffold(tmp_path / "demo")
    before_plan = Plan.load(root)
    check_before = before_plan.check()
    braid_before = before_plan.braid()

    events_dir = root / store.EVENTS_DIR
    events_dir.mkdir()
    (events_dir / store.EVENTS_FILE).write_text(
        '{"actor": "cli", "op": "add_node", "targets": ["x"]}\n', encoding="utf-8"
    )

    after_plan = Plan.load(root)
    assert after_plan.check() == check_before
    assert after_plan.braid() == braid_before
