"""
@file        tests/test_validate.py
@purpose     Every check rule triggers on the file that breaks it and stays quiet
             on one that doesn't: kinds, fields, dangling edges (including the
             three mention keys and their kind checks), dangling @id prose
             mentions, the cycle path, orphans (mention edges count, prose
             mentions don't), open dependencies, empty bodies, and the
             deterministic errors-first ordering.
@layer       tests
@tags        validation, findings, check, mentions
@related     kumihimo/core/validate.py (under test)
@design      PLAN.md §3.4, queue item K4; PLAN2.md §3.1-3.2, queue item K28
"""

from pathlib import Path

from kumihimo import Plan
from tests.conftest import PlanFactory


def messages(root: Path) -> list[str]:
    return [f.render() for f in Plan.load(root).check()]


def test_clean_two_node_plan_has_no_findings(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "a.md": "---\nkind: task\n---\nDo a.\n",
            "b.md": "---\nkind: task\nneeds: [a]\n---\nDo b after a.\n",
        }
    )
    assert Plan.load(root).check() == []


def test_unknown_and_missing_kind_are_errors(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "alien.md": "---\nkind: alien\nneeds: [bare]\n---\nBody.\n",
            "bare.md": "---\n---\nBody.\n",
        }
    )
    found = messages(root)
    assert any("unknown kind 'alien'" in m and "task" in m for m in found)
    assert any("bare: node has no kind" in m for m in found)


def test_field_breach_surfaces_through_check(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "t.md": "---\nkind: task\neffort: XL\nlinks: [t2]\n---\nBody.\n",
            "t2.md": "---\nkind: task\nlinks: [t]\n---\nBody.\n",
        }
    )
    assert any("S, M, L" in m for m in messages(root))


def test_dangling_targets_name_edge_kind_and_target(plan_dir: PlanFactory) -> None:
    text = "---\nkind: task\nneeds: [ghost]\nin: [nowhere]\nlinks: [void]\n---\nBody.\n"
    root = plan_dir({"t.md": text})
    found = messages(root)
    assert any("'needs' target 'ghost'" in m for m in found)
    assert any("'in' target 'nowhere'" in m for m in found)
    assert any("'links' target 'void'" in m for m in found)


def test_mention_targets_dangling_name_edge_kind_and_target(plan_dir: PlanFactory) -> None:
    text = "---\nkind: task\nagents: [nobody]\nskills: [nothing]\ntrains: [noone]\n---\nBody.\n"
    root = plan_dir({"t.md": text})
    found = messages(root)
    assert any("'agents' target 'nobody'" in m for m in found)
    assert any("'skills' target 'nothing'" in m for m in found)
    assert any("'trains' target 'noone'" in m for m in found)


def test_mention_target_right_kind_is_quiet(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\nruntime: human\n---\nDoes the work.\n",
            "iter.md": "---\nkind: skill\n---\nRuns a pass.\n",
            "t.md": "---\nkind: task\nagents: [wright]\nskills: [iter]\ntrains: [wright, iter]\n"
            "---\nBody.\n",
        }
    )
    found = messages(root)
    assert not any("expected" in m for m in found)


def test_mention_target_wrong_kind_is_error(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "notacrew.md": "---\nkind: task\n---\nJust a task.\n",
            "t.md": "---\nkind: task\nagents: [notacrew]\nskills: [notacrew]\ntrains: [notacrew]\n"
            "---\nBody.\n",
        }
    )
    found = messages(root)
    assert any("'agents' target 'notacrew' is kind task, expected agent" in m for m in found)
    assert any("'skills' target 'notacrew' is kind task, expected skill" in m for m in found)
    assert any(
        "'trains' target 'notacrew' is kind task, expected agent or skill" in m for m in found
    )


def test_mention_edges_count_for_orphan_connectivity(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "t.md": "---\nkind: task\nagents: [wright]\n---\nBody.\n",
        }
    )
    found = messages(root)
    assert not any("wright: orphan" in m for m in found)
    assert not any("t: orphan" in m for m in found)


def test_dangling_prose_mention_warns(plan_dir: PlanFactory) -> None:
    root = plan_dir({"t.md": "---\nkind: task\n---\nHand this to @wright.\n"})
    found = messages(root)
    assert any("body mentions '@wright' but no node 'wright' exists" in m for m in found)


def test_existing_prose_mention_is_quiet(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "t.md": "---\nkind: task\n---\nHand this to @wright.\n",
        }
    )
    found = messages(root)
    assert not any("body mentions" in m for m in found)


def test_prose_mention_does_not_rescue_orphan(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "t.md": "---\nkind: task\n---\nHand this to @wright.\n",
        }
    )
    found = messages(root)
    assert any("wright: orphan" in m for m in found)


def test_kindless_agents_mention_loads_with_findings_not_crash(plan_dir: PlanFactory) -> None:
    # PLAN2 §3.2's tolerance claim, tested directly: a node combining a
    # missing kind with the new mention keys still loads and checks — findings,
    # never an exception.
    root = plan_dir({"weird.md": "---\nagents: [nobody]\n---\nBody.\n"})
    plan = Plan.load(root)
    assert "weird" in plan.nodes
    assert plan.nodes["weird"].agents == ["nobody"]
    found = [f.render() for f in plan.check()]
    assert any("no kind" in m for m in found)
    assert any("'agents' target 'nobody' does not exist" in m for m in found)


def test_cycle_is_one_error_naming_the_path(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "a.md": "---\nkind: task\nneeds: [b]\n---\nBody.\n",
            "b.md": "---\nkind: task\nneeds: [a]\n---\nBody.\n",
        }
    )
    cycle_findings = [m for m in messages(root) if "dependency cycle" in m]
    assert cycle_findings == ["error: a: dependency cycle: a -> b -> a"]


def test_orphan_is_warning_and_connected_is_not(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "loner.md": "---\nkind: task\n---\nBody.\n",
            "a.md": "---\nkind: task\n---\nBody.\n",
            "b.md": "---\nkind: task\nneeds: [a]\n---\nBody.\n",
        }
    )
    found = messages(root)
    assert any("loner: orphan" in m for m in found)
    assert not any("a: orphan" in m or "b: orphan" in m for m in found)


def test_depending_on_open_decision_warns(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "algo.md": "---\nkind: decision\n---\nWhich algorithm?\n",
            "build.md": "---\nkind: task\nneeds: [algo]\n---\nBuild it.\n",
        }
    )
    assert any("still open" in m and "build" in m for m in messages(root))


def test_settled_decision_does_not_warn(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "algo.md": "---\nkind: decision\nstatus: settled\nchoice: x\n---\nSettled.\n",
            "build.md": "---\nkind: task\nneeds: [algo]\n---\nBuild it.\n",
        }
    )
    assert not any("still open" in m for m in messages(root))


def test_empty_body_warns(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "empty.md": "---\nkind: task\nlinks: [full]\n---\n",
            "full.md": "---\nkind: task\nlinks: [empty]\n---\nWords.\n",
        }
    )
    assert any("empty: empty body" in m for m in messages(root))


def test_errors_sort_before_warnings(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "zz-bad.md": "---\nkind: alien\nlinks: [ok]\n---\nBody.\n",
            "aa-loner.md": "---\nkind: task\n---\nBody.\n",
            "ok.md": "---\nkind: task\nlinks: [zz-bad]\n---\nBody.\n",
        }
    )
    findings = Plan.load(root).check()
    levels = [f.level for f in findings]
    assert levels == sorted(levels, key=lambda level: level != "error")
    assert findings[0].level == "error"
    assert findings[-1].level == "warning"
