"""
@file        tests/test_cli_verbs.py
@purpose     The M1 demo path, end to end through the real CLI: new → add →
             link → check, plus field coercion, error exit codes, --strict, and
             the cycle named in check output. Also covers K29's CLI surface:
             `braid --for`, `kumihimo crew`, `export --format jsonl` (gated on
             check errors like braid; mermaid stays ungated), a real
             subprocess check that stdout redirect emits LF, not CRLF, and
             `link`'s --agents/--skills/--trains mention flags (fold-in
             alongside K42/K44): each lands on disk, a wrong-kind target and a
             mixed-flag call both surface ops.link's own wording untouched.
@layer       tests
@tags        cli, verbs, integration, crew, for-agent, jsonl, encoding, mentions
@related     kumihimo/cli/app.py (the app under test),
             kumihimo/cli/common.py (the stdout/stderr reconfigure under test),
             tests/conftest.py (plan factory for pre-broken fixtures)
@design      PLAN.md §9 M1, queue item K6; PLAN2.md §3.3, §3.6-3.7, K29
"""

import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from kumihimo import Plan
from kumihimo.cli.app import app
from tests.conftest import PlanFactory

runner = CliRunner()
WIDE = {"COLUMNS": "250"}
CREW_DEMO = Path(__file__).resolve().parent / "fixtures" / "crew-demo"


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


def test_set_updates_title_fields_and_unsets(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    runner.invoke(app, ["new", plan], env=WIDE)
    runner.invoke(app, ["add", plan, "t", "--body", "b", "--field", "effort=S"], env=WIDE)
    result = runner.invoke(
        app,
        ["set", plan, "t", "--title", "Titled", "--field", "acceptance=a,b", "--unset", "effort"],
        env=WIDE,
    )
    assert result.exit_code == 0
    node = Plan.load(plan).nodes["t"]
    assert node.title == "Titled"
    assert node.fields["acceptance"] == ["a", "b"]
    assert "effort" not in node.fields
    missing = runner.invoke(app, ["set", plan, "ghost", "--title", "x"], env=WIDE)
    assert missing.exit_code == 2


def test_braid_for_flag_opens_with_grounding_line() -> None:
    result = runner.invoke(app, ["braid", str(CREW_DEMO), "--for", "wright"], env=WIDE)
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert lines[0] == "# Braid: Crew Demo"
    assert lines[1] == "*Ground with:* grep the repo for the symbol first, then check docs/"


def test_braid_for_unknown_kind_exits_2_naming_the_kind(tmp_path: Path) -> None:
    plan = str(tmp_path / "demo")
    runner.invoke(app, ["new", plan], env=WIDE)
    result = runner.invoke(app, ["braid", plan, "--for", "first-thread"], env=WIDE)
    assert result.exit_code == 2
    assert "is kind 'task', expected agent" in result.output


def test_crew_command_lists_the_roster() -> None:
    result = runner.invoke(app, ["crew", str(CREW_DEMO)], env=WIDE)
    assert result.exit_code == 0
    assert "wright" in result.output
    assert "iteration" in result.output
    assert "ward-postmortem" in result.output
    assert "3 crew member(s)" in result.output


def test_export_jsonl_round_trips_line_by_line() -> None:
    result = runner.invoke(app, ["export", str(CREW_DEMO), "--format", "jsonl"], env=WIDE)
    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line]
    assert len(lines) == 6  # every node in crew-demo, one line each
    records = [json.loads(line) for line in lines]
    assert [r["id"] for r in records] == sorted(r["id"] for r in records)
    by_id = {r["id"]: r for r in records}
    guard = by_id["build-guard"]
    assert guard["kind"] == "task"
    assert guard["edges"]["agents"] == ["wright"]
    assert guard["edges"]["skills"] == ["iteration"]
    assert guard["edges"]["links"] == [{"to": "ward-postmortem", "rel": "consult"}]
    assert guard["effective"]["status"] == "todo"  # kind default materialized
    retro = by_id["retro"]
    assert retro["edges"]["needs"] == ["build-guard"]
    assert retro["edges"]["trains"] == ["wright", "iteration"]


def test_export_unknown_format_exits_2() -> None:
    result = runner.invoke(app, ["export", str(CREW_DEMO), "--format", "yaml"], env=WIDE)
    assert result.exit_code == 2
    assert "unknown format 'yaml'" in result.output


def test_export_jsonl_gates_on_check_errors_through_the_cli(plan_dir: PlanFactory) -> None:
    root = plan_dir({"t.md": "---\nkind: task\nagents: [ghost]\n---\nDangling mention.\n"})
    result = runner.invoke(app, ["export", str(root), "--format", "jsonl"], env=WIDE)
    assert result.exit_code == 2
    assert "check error" in result.output
    # mermaid stays ungated on the same broken plan.
    mermaid_result = runner.invoke(app, ["export", str(root), "--format", "mermaid"], env=WIDE)
    assert mermaid_result.exit_code == 0


def test_link_agents_flag_lands_on_disk(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "t.md": "---\nkind: task\n---\nBody.\n",
            "bot.md": "---\nkind: agent\n---\nBody.\n",
        }
    )
    result = runner.invoke(app, ["link", str(root), "t", "--agents", "bot"], env=WIDE)
    assert result.exit_code == 0
    assert "now mentions agent" in result.output
    node = Plan.load(root).nodes["t"]
    assert node.agents == ["bot"]


def test_link_skills_and_trains_flags_land_on_disk(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "t.md": "---\nkind: task\n---\nBody.\n",
            "sk.md": "---\nkind: skill\n---\nBody.\n",
            "bot.md": "---\nkind: agent\n---\nBody.\n",
        }
    )
    skills_result = runner.invoke(app, ["link", str(root), "t", "--skills", "sk"], env=WIDE)
    assert skills_result.exit_code == 0
    assert "now mentions skill" in skills_result.output
    trains_result = runner.invoke(app, ["link", str(root), "t", "--trains", "bot"], env=WIDE)
    assert trains_result.exit_code == 0
    assert "now trains" in trains_result.output
    node = Plan.load(root).nodes["t"]
    assert node.skills == ["sk"]
    assert node.trains == ["bot"]


def test_link_agents_wrong_kind_exits_2_with_ops_wording(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "t.md": "---\nkind: task\n---\nBody.\n",
            "other.md": "---\nkind: task\n---\nBody.\n",
        }
    )
    result = runner.invoke(app, ["link", str(root), "t", "--agents", "other"], env=WIDE)
    assert result.exit_code == 2
    assert "is kind task, expected agent" in result.output


def test_link_mixing_needs_and_agents_exits_2_with_ops_wording(plan_dir: PlanFactory) -> None:
    # The CLI carries no second copy of the "exactly one" rule (link_cmd.py's
    # own header note) — this proves ops.link's own refusal reaches the shell
    # unchanged when a caller gives two mutually exclusive flags at once.
    root = plan_dir(
        {
            "t.md": "---\nkind: task\n---\nBody.\n",
            "u.md": "---\nkind: task\n---\nBody.\n",
            "bot.md": "---\nkind: agent\n---\nBody.\n",
        }
    )
    result = runner.invoke(
        app, ["link", str(root), "t", "--needs", "u", "--agents", "bot"], env=WIDE
    )
    assert result.exit_code == 2
    assert "give exactly one of" in result.output


def test_braid_stdout_redirect_has_no_crlf_and_matches_the_api_bytes() -> None:
    # A real subprocess, not CliRunner's in-memory capture: this is the only
    # way to actually exercise sys.stdout's text-mode newline translation,
    # which is where the Windows-specific CRLF bug lived. -c (not -m) so the
    # test needs no __main__.py and runs under the exact interpreter pytest
    # itself is using, no PATH/uv dependency.
    code = "from kumihimo.cli.app import main; main()"
    completed = subprocess.run(
        [sys.executable, "-c", code, "braid", str(CREW_DEMO)], capture_output=True
    )
    assert completed.returncode == 0, completed.stderr
    assert b"\r\n" not in completed.stdout
    api_text = Plan.load(CREW_DEMO).braid()
    assert completed.stdout.decode("utf-8") == api_text
