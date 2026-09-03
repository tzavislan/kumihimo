"""
@file        tests/test_ops.py
@purpose     The ops layer behaves: canonical files from add, comment-preserving
             updates, cycle-refusing links, tidy unlinks, mention edges
             (agents/skills/trains — existence and kind enforced, no cycle
             guard), renames that fix every referrer and the view layout
             without touching the renamed file's bytes, removes that refuse
             or strip references, and restores that bring a removed file
             back byte-for-byte.
@layer       tests
@tags        ops, mutations, referrer-fixup, cycle-guard, mentions, restore
@related     kumihimo/core/ops.py (under test)
@design      PLAN.md §7.1 invariant 1, queue item K5; PLAN2.md §3.2, queue
             item K28; queue item K45
"""

import hashlib
import json

import pytest

from kumihimo import KumihimoError, Plan
from kumihimo.core import ops, store
from tests.conftest import PlanFactory

BODIED = "---\nkind: task\n---\nBody.\n"


def test_add_writes_canonical_file(plan_dir: PlanFactory) -> None:
    root = plan_dir({"base.md": BODIED})
    node = ops.add_node(
        root,
        "guard",
        "task",
        title="Guard the API",
        body="Middleware first.\n",
        fields={"effort": "M"},
        needs=("base",),
    )
    assert node.needs == ["base"]
    text = (root / "nodes" / "guard.md").read_text(encoding="utf-8")
    assert text == (
        "---\nkind: task\ntitle: Guard the API\nneeds: [base]\neffort: M\n---\nMiddleware first.\n"
    )


def test_add_refuses_duplicates_bad_slugs_unknown_kinds_and_dangling(
    plan_dir: PlanFactory,
) -> None:
    root = plan_dir({"base.md": BODIED})
    with pytest.raises(KumihimoError, match="already exists"):
        ops.add_node(root, "base", "task")
    with pytest.raises(KumihimoError, match="not a valid id"):
        ops.add_node(root, "Bad_Name", "task")
    with pytest.raises(KumihimoError, match="unknown kind"):
        ops.add_node(root, "x", "alien")
    with pytest.raises(KumihimoError, match="does not exist"):
        ops.add_node(root, "x", "task", needs=("ghost",))


def test_update_preserves_comments_and_sets_fields(plan_dir: PlanFactory) -> None:
    text = "---\n# why: measured on 8/20\nkind: task\neffort: M\n---\nBody.\n"
    root = plan_dir({"t.md": text})
    node = ops.update_node(root, "t", title="Tuned", set_fields={"effort": "L", "status": "doing"})
    assert node.title == "Tuned"
    assert node.fields["effort"] == "L"
    saved = (root / "nodes" / "t.md").read_text(encoding="utf-8")
    assert "# why: measured on 8/20" in saved
    assert "effort: L" in saved


def test_update_refuses_reserved_keys_and_unknown_kind(plan_dir: PlanFactory) -> None:
    root = plan_dir({"t.md": BODIED})
    with pytest.raises(KumihimoError, match="dedicated op"):
        ops.update_node(root, "t", set_fields={"needs": ["x"]})
    with pytest.raises(KumihimoError, match="unknown kind"):
        ops.update_node(root, "t", kind="alien")


def test_update_body_and_unset(plan_dir: PlanFactory) -> None:
    root = plan_dir({"t.md": "---\nkind: task\neffort: M\n---\nOld.\n"})
    node = ops.update_node(root, "t", body="New body.\n", unset_fields=("effort",))
    assert node.body == "New body.\n"
    assert "effort" not in node.fields
    with pytest.raises(KumihimoError, match="no field"):
        ops.update_node(root, "t", unset_fields=("effort",))


def test_link_needs_appends_and_refuses_duplicates_and_self(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": BODIED})
    node = ops.link(root, "b", needs="a")
    assert node.needs == ["a"]
    assert "needs: [a]" in (root / "nodes" / "b.md").read_text(encoding="utf-8")
    with pytest.raises(KumihimoError, match="already needs"):
        ops.link(root, "b", needs="a")
    with pytest.raises(KumihimoError, match="itself"):
        ops.link(root, "a", needs="a")


def test_link_refuses_cycles_and_leaves_files_untouched(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "a.md": "---\nkind: task\nneeds: [b]\n---\nBody.\n",
            "b.md": BODIED,
        }
    )
    before = (root / "nodes" / "b.md").read_bytes()
    with pytest.raises(KumihimoError, match="closes a cycle"):
        ops.link(root, "b", needs="a")
    assert (root / "nodes" / "b.md").read_bytes() == before


def test_link_membership_and_annotation(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "m.md": "---\nkind: milestone\n---\nShip it.\n",
            "t.md": BODIED,
            "r.md": "---\nkind: risk\n---\nDanger.\n",
        }
    )
    assert ops.link(root, "t", in_="m").in_ == ["m"]
    node = ops.link(root, "t", to="r", rel="threatened-by")
    assert [(entry.to, entry.rel) for entry in node.links] == [("r", "threatened-by")]
    plain = ops.link(root, "t", to="m")
    assert ("m", "see-also") in [(entry.to, entry.rel) for entry in plain.links]


def test_link_mentions_append_and_refuse_duplicates(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "iter.md": "---\nkind: skill\n---\nRuns a pass.\n",
            "t.md": BODIED,
        }
    )
    assert ops.link(root, "t", agents="wright").agents == ["wright"]
    assert ops.link(root, "t", skills="iter").skills == ["iter"]
    assert ops.link(root, "t", trains="wright").trains == ["wright"]
    assert ops.link(root, "t", trains="iter").trains == ["wright", "iter"]
    text = (root / "nodes" / "t.md").read_text(encoding="utf-8")
    assert "agents: [wright]" in text
    assert "skills: [iter]" in text
    assert "trains: [wright, iter]" in text
    with pytest.raises(KumihimoError, match="already has"):
        ops.link(root, "t", agents="wright")


def test_link_mentions_refuse_wrong_kind(plan_dir: PlanFactory) -> None:
    root = plan_dir({"t.md": BODIED, "other.md": BODIED})
    with pytest.raises(KumihimoError, match="is kind task, expected agent"):
        ops.link(root, "t", agents="other")
    with pytest.raises(KumihimoError, match="is kind task, expected skill"):
        ops.link(root, "t", skills="other")
    with pytest.raises(KumihimoError, match="expected agent or skill"):
        ops.link(root, "t", trains="other")


def test_link_give_exactly_one_edge_covers_mentions(plan_dir: PlanFactory) -> None:
    root = plan_dir({"wright.md": "---\nkind: agent\n---\nDoes the work.\n", "t.md": BODIED})
    with pytest.raises(KumihimoError, match="exactly one of"):
        ops.link(root, "t", agents="wright", skills="wright")


def test_unlink_mentions_drop_key_when_last_edge_goes(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "iter.md": "---\nkind: skill\n---\nRuns a pass.\n",
            "t.md": "---\nkind: task\nagents: [wright]\nskills: [iter]\ntrains: [wright]\n"
            "---\nBody.\n",
        }
    )
    assert ops.unlink(root, "t", agents="wright").agents == []
    assert ops.unlink(root, "t", skills="iter").skills == []
    node = ops.unlink(root, "t", trains="wright")
    assert node.trains == []
    text = (root / "nodes" / "t.md").read_text(encoding="utf-8")
    assert "agents" not in text
    assert "skills" not in text
    assert "trains" not in text
    with pytest.raises(KumihimoError, match="no agents entry"):
        ops.unlink(root, "t", agents="wright")


def test_unlink_drops_key_when_last_edge_goes(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": "---\nkind: task\nneeds: [a]\n---\nBody.\n"})
    node = ops.unlink(root, "b", needs="a")
    assert node.needs == []
    assert "needs" not in (root / "nodes" / "b.md").read_text(encoding="utf-8")
    with pytest.raises(KumihimoError, match="no needs entry"):
        ops.unlink(root, "b", needs="a")


def test_rename_fixes_referrers_and_view_without_touching_renamed_bytes(
    plan_dir: PlanFactory,
) -> None:
    root = plan_dir(
        {
            "old-name.md": "---\nkind: task\n# a comment that must survive\n---\nBody.\n",
            "dep.md": "---\nkind: task\nneeds: [old-name]\n---\nBody.\n",
            "grouped.md": "---\nkind: task\nin: old-name\n---\nBody.\n",
            "annot.md": "---\nkind: task\nlinks:\n  - {to: old-name, rel: informs}\n---\nBody.\n",
        }
    )
    (root / "view.yaml").write_bytes(b"layout:\n  old-name: {x: 10, y: 20}\n")
    before = (root / "nodes" / "old-name.md").read_bytes()
    ops.rename_node(root, "old-name", "new-name")
    assert not (root / "nodes" / "old-name.md").exists()
    assert (root / "nodes" / "new-name.md").read_bytes() == before
    plan = Plan.load(root)
    assert plan.nodes["dep"].needs == ["new-name"]
    assert plan.nodes["grouped"].in_ == ["new-name"]
    assert plan.nodes["annot"].links[0].to == "new-name"
    assert "new-name" in (root / "view.yaml").read_text(encoding="utf-8")
    assert "old-name" not in (root / "view.yaml").read_text(encoding="utf-8")
    assert plan.check() == []


def test_rename_fixes_mention_referrers(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "old-name.md": BODIED,
            "assigned.md": "---\nkind: task\nagents: [old-name]\n---\nBody.\n",
            "skilled.md": "---\nkind: task\nskills: [old-name]\n---\nBody.\n",
            "trained.md": "---\nkind: task\ntrains: old-name\n---\nBody.\n",
        }
    )
    ops.rename_node(root, "old-name", "new-name")
    plan = Plan.load(root)
    assert plan.nodes["assigned"].agents == ["new-name"]
    assert plan.nodes["skilled"].skills == ["new-name"]
    assert plan.nodes["trained"].trains == ["new-name"]


def test_rename_target_keeps_scalar_mention_shape_and_comment_byte_exact(
    plan_dir: PlanFactory,
) -> None:
    # A scalar mention (not a list) plus a trailing comment: renaming the
    # TARGET must rewrite only the value, in place, as a scalar — comment and
    # body untouched. Byte-exact, not just re-parsed, so a stray reflow or a
    # scalar-to-list promotion would fail this test even if the graph still
    # read correctly afterward.
    trainer = (
        "---\n"
        "kind: task\n"
        "trains: old-target  # keep this reviewer honest\n"
        "---\n"
        "Retro every milestone.\n"
    )
    root = plan_dir({"old-target.md": BODIED, "trainer.md": trainer})
    ops.rename_node(root, "old-target", "new-target")
    expected = trainer.replace("trains: old-target", "trains: new-target")
    assert (root / "nodes" / "trainer.md").read_bytes() == expected.encode("utf-8")


def test_rename_into_namespace_and_collision_refusal(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED, "b.md": BODIED})
    node = ops.rename_node(root, "a", "auth/login")
    assert node.id == "auth/login"
    with pytest.raises(KumihimoError, match="already exists"):
        ops.rename_node(root, "auth/login", "b")


def test_remove_refuses_when_referenced_then_strips_with_force(
    plan_dir: PlanFactory,
) -> None:
    root = plan_dir(
        {
            "target.md": BODIED,
            "dep.md": "---\nkind: task\nneeds: [target]\n---\nBody.\n",
            "annot.md": "---\nkind: task\nlinks: [target]\n---\nBody.\n",
        }
    )
    (root / "view.yaml").write_bytes(b"layout:\n  target: {x: 1, y: 2}\n")
    with pytest.raises(KumihimoError, match="dep"):
        ops.remove_node(root, "target")
    referrers = ops.remove_node(root, "target", force=True)
    assert referrers == ["annot", "dep"]
    assert not (root / "nodes" / "target.md").exists()
    plan = Plan.load(root)
    assert plan.nodes["dep"].needs == []
    assert plan.nodes["annot"].links == []
    assert "target" not in (root / "view.yaml").read_text(encoding="utf-8")


def test_remove_force_strips_mention_referrers(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "assigned.md": "---\nkind: task\nagents: [wright]\n---\nBody.\n",
            "trained.md": "---\nkind: task\ntrains: wright\n---\nBody.\n",
        }
    )
    with pytest.raises(KumihimoError, match="assigned"):
        ops.remove_node(root, "wright")
    referrers = ops.remove_node(root, "wright", force=True)
    assert referrers == ["assigned", "trained"]
    plan = Plan.load(root)
    assert plan.nodes["assigned"].agents == []
    assert plan.nodes["trained"].trains == []


def test_remove_unreferenced_is_quiet(plan_dir: PlanFactory) -> None:
    root = plan_dir({"solo.md": BODIED})
    assert ops.remove_node(root, "solo") == []
    assert not (root / "nodes" / "solo.md").exists()


def test_ops_reject_missing_nodes_with_one_phrasing(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    for call in (
        lambda: ops.update_node(root, "ghost", title="x"),
        lambda: ops.link(root, "ghost", needs="a"),
        lambda: ops.unlink(root, "ghost", needs="a"),
        lambda: ops.rename_node(root, "ghost", "new"),
        lambda: ops.remove_node(root, "ghost"),
    ):
        with pytest.raises(KumihimoError, match="no node 'ghost'"):
            call()


def test_path_traversal_ids_are_rejected(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    for bad in ("../escape", "a/../../b", ".hidden", "a//b"):
        with pytest.raises(KumihimoError, match="not a valid id"):
            ops.add_node(root, bad, "task")
        with pytest.raises(KumihimoError, match="not a valid id"):
            ops.rename_node(root, "a", bad)


# --- K45: restore_node, remove's real inverse ------------------------------


def test_restore_round_trips_exact_bytes(plan_dir: PlanFactory) -> None:
    # A comment-laden, CRLF fixture: remove reads a file's exact prior bytes
    # before deleting it (mirrored here by reading the file ourselves the
    # same way store.py does), and restore must reproduce them precisely
    # enough that a fresh sha256 matches — not just "loads the same," but
    # byte-exact, including the \r\n line endings and the comment.
    text = (
        "---\r\n"
        "kind: task\r\n"
        "# why: keep this reviewer honest\r\n"
        "title: CRLF fixture\r\n"
        "---\r\n"
        "Body with a trailing comment.\r\n"
    )
    root = plan_dir({"crlf.md": text})
    path = root / "nodes" / "crlf.md"
    before = path.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()

    ops.remove_node(root, "crlf")
    assert not path.exists()

    node = ops.restore_node(root, "crlf", before.decode("utf-8"))
    assert node.id == "crlf"
    after = path.read_bytes()
    assert after == before
    assert hashlib.sha256(after).hexdigest() == before_hash


def test_restore_refuses_when_the_id_already_exists(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    with pytest.raises(KumihimoError, match="already exists"):
        ops.restore_node(root, "a", BODIED)
    # Refused, not clobbered: the existing file is untouched.
    assert (root / "nodes" / "a.md").read_bytes() == BODIED.encode("utf-8")


def test_restore_brings_back_the_view_yaml_position(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    (root / "view.yaml").write_bytes(b"layout:\n  a: {x: 10, y: 20}\n")
    content = (root / "nodes" / "a.md").read_bytes().decode("utf-8")

    ops.remove_node(root, "a")
    assert "a: {x: 10, y: 20}" not in (root / "view.yaml").read_text(encoding="utf-8")

    ops.restore_node(root, "a", content, position=(10, 20))
    view = (root / "view.yaml").read_text(encoding="utf-8")
    assert "a: {x: 10, y: 20}" in view


def test_restore_without_a_position_leaves_view_yaml_alone(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    content = (root / "nodes" / "a.md").read_bytes().decode("utf-8")
    ops.remove_node(root, "a")
    ops.restore_node(root, "a", content)
    assert not (root / "view.yaml").exists()


def test_restore_logs_event_with_default_actor_api(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    content = (root / "nodes" / "a.md").read_bytes().decode("utf-8")
    ops.remove_node(root, "a")
    ops.restore_node(root, "a", content)
    events_path = root / store.EVENTS_DIR / store.EVENTS_FILE
    lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert lines[-1] == {"actor": "api", "op": "restore_node", "targets": ["a"]}


def test_restore_rejects_invalid_slugs(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": BODIED})
    for bad in ("Bad_Name", "../escape", ".hidden"):
        with pytest.raises(KumihimoError, match="not a valid id"):
            ops.restore_node(root, bad, BODIED)
