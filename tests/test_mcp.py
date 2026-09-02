"""
@file        tests/test_mcp.py
@purpose     The MCP tools behave identically to their ops/CLI twins: reads
             carry the right shapes, mutations land on disk, errors keep their
             KumihimoError messages, ready implements the satisfaction rule,
             and the server registers all eleven tools.
@layer       tests
@tags        mcp, tools, ready
@related     kumihimo/mcp/tools.py (under test),
             kumihimo/mcp/server.py (registration smoke)
@design      PLAN.md §6.1, roadmap item mcp-tools
"""

import asyncio
from pathlib import Path

import pytest

from kumihimo import KumihimoError, Plan
from kumihimo.mcp import tools
from kumihimo.mcp.server import build_server
from tests.conftest import PlanFactory

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "apiguard"


def test_get_plan_elides_bodies_and_lists_everything() -> None:
    result = tools.get_plan(EXAMPLE)
    assert result["plan"] == "API Guard"
    assert len(result["nodes"]) == 7
    assert all("body" not in node for node in result["nodes"])
    assert result["kinds"] == [
        "agent",
        "decision",
        "milestone",
        "question",
        "reference",
        "risk",
        "skill",
        "task",
    ]


def test_get_node_carries_body_and_effective_fields() -> None:
    node = tools.get_node(EXAMPLE, "rate-limit-core")
    assert "Fail *open* on Redis errors" in node["body"]
    assert node["effective_fields"]["status"] == "todo"  # default materialized
    assert "status" not in node["fields"]  # but never written into the file


def test_mutations_land_on_disk_and_errors_keep_messages(plan_dir: PlanFactory) -> None:
    root = plan_dir({"a.md": "---\nkind: task\n---\nA.\n"})
    tools.add_node(root, "b", "task", body="B.", needs=["a"])
    assert Plan.load(root).nodes["b"].needs == ["a"]
    tools.update_node(root, "b", set_fields={"status": "doing"})
    tools.rename_node(root, "b", "c")
    assert "c" in Plan.load(root).nodes
    with pytest.raises(KumihimoError, match="closes a cycle"):
        tools.link(root, "a", needs="c")
    tools.unlink(root, "c", needs="a")
    assert tools.remove_node(root, "c")["removed"] == "c"
    assert set(Plan.load(root).nodes) == {"a"}


def test_check_and_braid_match_library_behavior() -> None:
    assert tools.check(EXAMPLE) == []
    result = tools.braid(EXAMPLE, strategy="linear")
    assert result["text"] == Plan.load(EXAMPLE).braid(strategy="linear")
    assert result["order"][0] == "api-endpoints"
    dry = tools.braid(EXAMPLE, in_="ship-guarded-api", dry=True)
    assert dry["text"].startswith("braid order")


def test_ready_applies_the_satisfaction_rule(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "done-dep.md": "---\nkind: task\nstatus: done\n---\nDone.\n",
            "open-decision.md": "---\nkind: decision\n---\nUndecided.\n",
            "settled.md": "---\nkind: decision\nstatus: settled\nchoice: x\n---\nSettled.\n",
            "ready-one.md": "---\nkind: task\nneeds: [done-dep, settled]\n---\nGo.\n",
            "blocked-one.md": "---\nkind: task\nneeds: [open-decision]\n---\nWait.\n",
            "doing-one.md": "---\nkind: task\nstatus: doing\nlinks: [done-dep]\n---\nBusy.\n",
            "no-status.md": "---\nkind: milestone\nlinks: [done-dep]\n---\nM.\n",
        }
    )
    ready_ids = [node["id"] for node in tools.ready(root)]
    assert "ready-one" in ready_ids  # deps done and settled
    assert "blocked-one" not in ready_ids  # open decision blocks
    assert "doing-one" not in ready_ids  # own status not todo
    assert "no-status" not in ready_ids  # statusless kinds are never work items
    assert "done-dep" not in ready_ids  # already done


def test_roadmap_stays_structurally_clean() -> None:
    # The roadmap's statuses move as work completes (an earlier version of
    # this test pinned them and broke the moment dogfooding marked M3 done),
    # so pin only what must always hold: the plan validates clean and ready()
    # never surfaces a node whose own status isn't todo.
    root = Path("plans") / "roadmap"
    assert Plan.load(root).check() == []
    for node in tools.ready(root):
        assert node["fields"].get("status", "todo") == "todo"


def test_server_registers_all_eleven_tools() -> None:
    server = build_server(EXAMPLE)
    listed = asyncio.run(server.list_tools())
    names = sorted(tool.name for tool in listed)
    assert names == [
        "add_node",
        "braid",
        "check",
        "get_node",
        "get_plan",
        "link",
        "ready",
        "remove_node",
        "rename_node",
        "unlink",
        "update_node",
    ]
