"""
@file        tests/test_cli_verbs.py
@purpose     The M1 demo path, end to end through the real CLI: new → add →
             link → check, plus field coercion, error exit codes, --strict, and
             the cycle named in check output.
@layer       tests
@tags        cli, verbs, integration
@related     kumihimo/cli/app.py (the app under test),
             tests/conftest.py (plan factory for pre-broken fixtures)
@design      PLAN.md §9 M1, queue item K6
"""

from pathlib import Path

from typer.testing import CliRunner

from kumihimo import Plan
from kumihimo.cli.app import app
from tests.conftest import PlanFactory

runner = CliRunner()
WIDE = {"COLUMNS": "250"}


def test_new_add_link_check_happy_path(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    result = runner.invoke(app, ["new", plan], env=WIDE)
    assert result.exit_code == 0
    assert "braided a new plan" in result.output

    result = runner.invoke(
        app, ["add", plan, "api", "--kind", "task", "--body", "Define endpoints."], env=WIDE
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "add",
            plan,
            "guard",
            "--kind",
            "task",
            "--body",
            "Rate limit the API.",
            "--needs",
            "api",
            "--field",
            "effort=M",
            "--field",
            "acceptance=429 on breach,retry-after set",
        ],
        env=WIDE,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        app, ["link", plan, "guard", "--to", "api", "--rel", "informs"], env=WIDE
    )
    assert result.exit_code == 0

    result = runner.invoke(app, ["check", plan], env=WIDE)
    assert result.exit_code == 0
    assert "0 error(s)" in result.output

    loaded = Plan.load(plan)
    assert loaded.nodes["guard"].fields["acceptance"] == ["429 on breach", "retry-after set"]
    assert loaded.nodes["guard"].fields["effort"] == "M"


def test_strict_fails_on_warnings(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    runner.invoke(app, ["new", plan], env=WIDE)
    result = runner.invoke(app, ["check", plan, "--strict"], env=WIDE)
    assert result.exit_code == 1  # the starter node is an orphan warning


def test_add_duplicate_exits_2_with_message(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    runner.invoke(app, ["new", plan], env=WIDE)
    runner.invoke(app, ["add", plan, "x", "--body", "b"], env=WIDE)
    result = runner.invoke(app, ["add", plan, "x", "--body", "b"], env=WIDE)
    assert result.exit_code == 2
    assert "already exists" in result.output


def test_new_refuses_existing_plan(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    runner.invoke(app, ["new", plan], env=WIDE)
    result = runner.invoke(app, ["new", plan], env=WIDE)
    assert result.exit_code == 2
    assert "already" in result.output


def test_check_names_the_cycle_and_exits_1(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "a.md": "---\nkind: task\nneeds: [b]\n---\nBody.\n",
            "b.md": "---\nkind: task\nneeds: [a]\n---\nBody.\n",
        }
    )
    result = runner.invoke(app, ["check", str(root)], env=WIDE)
    assert result.exit_code == 1
    assert "a -> b -> a" in result.output


def test_link_cycle_refusal_through_cli(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "a.md": "---\nkind: task\nneeds: [b]\n---\nBody.\n",
            "b.md": "---\nkind: task\n---\nBody.\n",
        }
    )
    result = runner.invoke(app, ["link", str(root), "b", "--needs", "a"], env=WIDE)
    assert result.exit_code == 2
    assert "closes a cycle" in result.output


def test_check_on_not_a_plan_exits_2(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tmp_path)], env=WIDE)
    assert result.exit_code == 2
    assert "not a kumihimo plan" in result.output
