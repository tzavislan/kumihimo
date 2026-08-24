"""
@file        tests/test_ops.py
@purpose     The ops layer behaves: canonical files from add, comment-preserving
             updates, cycle-refusing links, tidy unlinks, renames that fix every
             referrer and the view layout without touching the renamed file's
             bytes, and removes that refuse or strip references.
@layer       tests
@tags        ops, mutations, referrer-fixup, cycle-guard
@related     kumihimo/core/ops.py (under test)
@design      PLAN.md §7.1 invariant 1, queue item K5
"""

from pathlib import Path

import pytest

from kumihimo import KumihimoError, Plan
from kumihimo.core import ops
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
