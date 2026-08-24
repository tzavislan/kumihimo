"""
@file        tests/test_example_apiguard.py
@purpose     Holds the shipped example to its promises: it validates clean, its
             braid order is deterministic and exactly what the graph implies, a
             hand-introduced cycle is named by check, and a one-field edit is a
             one-line diff.
@layer       tests
@tags        example, integration, m1-demo
@related     examples/apiguard (the fixture),
             kumihimo/core/graph.py (the order this pins)
@design      PLAN.md §9 M1, queue item K7
"""

import shutil
from pathlib import Path

from typer.testing import CliRunner

from kumihimo import Plan
from kumihimo.cli.app import app
from kumihimo.core import graph, ops

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "apiguard"
runner = CliRunner()


def copy_example(tmp_path: Path) -> Path:
    target = tmp_path / "apiguard"
    shutil.copytree(EXAMPLE, target)
    return target


def test_example_checks_completely_clean() -> None:
    plan = Plan.load(EXAMPLE)
    assert plan.check() == []
    assert set(plan.nodes) == {
        "api-endpoints",
        "headers-and-429",
        "per-org-quotas",
        "pick-algorithm",
        "rate-limit-core",
        "redis-outage",
        "ship-guarded-api",
    }


def test_example_braid_order_is_pinned() -> None:
    plan = Plan.load(EXAMPLE)
    assert graph.braid_order(plan.nodes) == [
        "api-endpoints",
        "per-org-quotas",
        "pick-algorithm",
        "rate-limit-core",
        "headers-and-429",
        "redis-outage",
        "ship-guarded-api",
    ]


def test_hand_introduced_cycle_is_named_by_check(tmp_path: Path) -> None:
    root = copy_example(tmp_path)
    target = root / "nodes" / "api-endpoints.md"
    text = target.read_text(encoding="utf-8")
    target.write_text(
        text.replace("in: [ship-guarded-api]", "in: [ship-guarded-api]\nneeds: [headers-and-429]"),
        encoding="utf-8",
        newline="",
    )
    result = runner.invoke(app, ["check", str(root)], env={"COLUMNS": "250"})
    assert result.exit_code == 1
    assert "api-endpoints -> headers-and-429 -> rate-limit-core -> api-endpoints" in result.output


def test_field_edit_is_a_one_line_diff(tmp_path: Path) -> None:
    root = copy_example(tmp_path)
    target = root / "nodes" / "rate-limit-core.md"
    before = target.read_text(encoding="utf-8").splitlines()
    ops.update_node(root, "rate-limit-core", set_fields={"effort": "L"})
    after = target.read_text(encoding="utf-8").splitlines()
    assert len(before) == len(after)
    changed = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert changed == [("effort: M", "effort: L")]
