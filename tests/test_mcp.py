"""
@file        tests/test_mcp.py
@purpose     The MCP tools behave identically to their ops/CLI twins: reads
             carry the right shapes, mutations land on disk, errors keep their
             KumihimoError messages, link/unlink grow the three mention
             kwargs exactly like ops.link/unlink (K36: kind-checked,
             exactly-one-of, same wording as the HTTP layer since both are
             thin, unwrapped callers of the same ops functions), get_plan/
             get_node surface those same mentions on read (K36 extension:
             _summary's shape mirrors payload.py's — agents/skills/trains
             always present as a list, empty rather than omitted), ready
             implements the satisfaction rule (its for_agent filter validated
             exactly like braid's --for), crew lists the roster (consult
             counts scoped to reference targets only), braid's for_agent
             matches the CLI's --for, and the server registers all twelve
             tools.
@layer       tests
@tags        mcp, tools, ready, crew, for-agent, mentions
@related     kumihimo/mcp/tools.py (under test),
             kumihimo/mcp/server.py (registration smoke)
@design      PLAN.md §6.1, PLAN2.md §3.3 §3.6, roadmap item mcp-tools, K36
"""

import asyncio
from pathlib import Path

import pytest

from kumihimo import KumihimoError, Plan
from kumihimo.mcp import tools
from kumihimo.mcp.server import build_server
from tests.conftest import PlanFactory

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "apiguard"
CREW_DEMO = Path(__file__).resolve().parent / "fixtures" / "crew-demo"


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


def test_link_and_unlink_mention_edges(plan_dir: PlanFactory) -> None:
    # Trigger: agents=/skills=/trains= round-trip through link then unlink,
    # mirroring test_ops_api.py's HTTP-layer coverage of the same three keys
    # (K36) — both are thin, unwrapped callers of core.ops.link/unlink.
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nWright.\n",
            "iteration.md": "---\nkind: skill\n---\nIteration.\n",
            "a.md": "---\nkind: task\n---\nA.\n",
        }
    )
    for key, target in (("agents", "wright"), ("skills", "iteration"), ("trains", "wright")):
        tools.link(root, "a", **{key: target})
    node = Plan.load(root).nodes["a"]
    assert node.agents == ["wright"]
    assert node.skills == ["iteration"]
    assert node.trains == ["wright"]

    tools.unlink(root, "a", agents="wright")
    assert Plan.load(root).nodes["a"].agents == []


def test_link_mention_wrong_kind_names_the_kind(plan_dir: PlanFactory) -> None:
    # Non-trigger for the kind rule: "b" exists but isn't kind agent.
    root = plan_dir({"a.md": "---\nkind: task\n---\nA.\n", "b.md": "---\nkind: task\n---\nB.\n"})
    with pytest.raises(KumihimoError, match="'agents' target 'b' is kind task, expected agent"):
        tools.link(root, "a", agents="b")


def test_unlink_absent_mention_errors(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {"wright.md": "---\nkind: agent\n---\nWright.\n", "a.md": "---\nkind: task\n---\nA.\n"}
    )
    with pytest.raises(KumihimoError, match="'a' has no agents entry 'wright'"):
        tools.unlink(root, "a", agents="wright")


def test_link_exactly_one_of_grows_to_six_kwargs(plan_dir: PlanFactory) -> None:
    # The kwarg list grew from three (needs/in_/to) to six (K36); core.ops
    # still enforces exactly one being set, MCP's tool just forwards all six.
    root = plan_dir(
        {"wright.md": "---\nkind: agent\n---\nWright.\n", "a.md": "---\nkind: task\n---\nA.\n"}
    )
    with pytest.raises(KumihimoError, match="give exactly one of needs=, in_=, to=, agents="):
        tools.link(root, "a", agents="wright", trains="wright")
    with pytest.raises(KumihimoError, match="give exactly one of needs=, in_=, to=, agents="):
        tools.unlink(root, "a")


def test_get_node_and_get_plan_carry_mention_edges(plan_dir: PlanFactory) -> None:
    # Trigger: a node with all three mention keys populated, read back
    # through both get_node and get_plan — the K36 read-side extension,
    # mirroring test_server.py's test_payload_carries_mention_edges so an
    # MCP reader and the HTTP canvas never disagree on a node's shape.
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nWright.\n",
            "iteration.md": "---\nkind: skill\n---\nIteration.\n",
            "build.md": (
                "---\nkind: task\nagents: [wright]\nskills: [iteration]\n"
                "trains: [wright, iteration]\n---\nBuild.\n"
            ),
        }
    )
    node = tools.get_node(root, "build")
    assert node["agents"] == ["wright"]
    assert node["skills"] == ["iteration"]
    assert node["trains"] == ["wright", "iteration"]

    plan = tools.get_plan(root)
    build_summary = next(n for n in plan["nodes"] if n["id"] == "build")
    assert build_summary["agents"] == ["wright"]
    assert build_summary["skills"] == ["iteration"]
    assert build_summary["trains"] == ["wright", "iteration"]
    # Non-trigger: a node that mentions nothing gets empty lists, not
    # missing keys.
    agent_summary = next(n for n in plan["nodes"] if n["id"] == "wright")
    assert agent_summary["agents"] == []
    assert agent_summary["skills"] == []
    assert agent_summary["trains"] == []


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


def test_ready_for_agent_filters_by_agents_key_only(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            "iter.md": "---\nkind: skill\n---\nRuns a pass.\n",
            "mine.md": "---\nkind: task\nagents: [wright]\n---\nAssigned to Wright.\n",
            "not-mine.md": "---\nkind: task\n---\nUnassigned.\n",
            "via-skill.md": "---\nkind: task\nskills: [iter]\n---\nMentions the skill.\n",
        }
    )
    ids = [node["id"] for node in tools.ready(root, for_agent="wright")]
    assert ids == ["mine"]  # skills:/trains: mentions of wright don't count


def test_ready_for_agent_missing_id_errors_like_braid_for() -> None:
    with pytest.raises(KumihimoError, match="--for: no node 'ghost'"):
        tools.ready(EXAMPLE, for_agent="ghost")


def test_ready_for_agent_wrong_kind_names_the_kind(plan_dir: PlanFactory) -> None:
    root = plan_dir({"t.md": "---\nkind: task\n---\nBody.\n"})
    with pytest.raises(KumihimoError, match="'t' is kind 'task', expected agent"):
        tools.ready(root, for_agent="t")


def test_braid_for_agent_matches_the_library() -> None:
    result = tools.braid(CREW_DEMO, strategy="grouped", for_agent="wright")
    assert result["text"] == Plan.load(CREW_DEMO).braid(strategy="grouped", for_agent="wright")
    assert result["text"].startswith("# Braid: Crew Demo\n*Ground with:*")


def test_crew_lists_the_roster_sorted_by_kind_then_id() -> None:
    entries = tools.crew(CREW_DEMO)
    # Sorted by kind then id: "agent" < "reference" < "skill".
    assert [e["id"] for e in entries] == ["wright", "ward-postmortem", "iteration"]
    wright = entries[0]
    assert wright["kind"] == "agent"
    assert wright["fields"]["trained"] == "2026-08-24"  # a string, never a date
    assert wright["mentions"] == {"agents": 1, "trains": 1}  # build-guard, retro
    reference = entries[1]
    assert reference["kind"] == "reference"
    assert reference["consulted_by"] == 1  # build-guard's one consult-link


def test_crew_consult_count_only_counts_reference_targets(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "wright.md": "---\nkind: agent\n---\nDoes the work.\n",
            # rel=consult, but the target is kind agent, not reference — this
            # is not a consult-link (render.py's *Consult:* rule agrees) and
            # must not inflate anyone's consulted_by count.
            "other.md": (
                "---\nkind: agent\nlinks: [{to: wright, rel: consult}]\n---\nAlso an agent.\n"
            ),
        }
    )
    entries = tools.crew(root)
    wright = next(e for e in entries if e["id"] == "wright")
    assert wright["consulted_by"] == 0


def test_roadmap_stays_structurally_clean() -> None:
    # The roadmap's statuses move as work completes (an earlier version of
    # this test pinned them and broke the moment dogfooding marked M3 done),
    # so pin only what must always hold: the plan validates clean and ready()
    # never surfaces a node whose own status isn't todo.
    root = Path("plans") / "roadmap"
    assert Plan.load(root).check() == []
    for node in tools.ready(root):
        assert node["fields"].get("status", "todo") == "todo"


def test_server_registers_all_twelve_tools() -> None:
    server = build_server(EXAMPLE)
    listed = asyncio.run(server.list_tools())
    names = sorted(tool.name for tool in listed)
    assert names == [
        "add_node",
        "braid",
        "check",
        "crew",
        "get_node",
        "get_plan",
        "link",
        "ready",
        "remove_node",
        "rename_node",
        "unlink",
        "update_node",
    ]
