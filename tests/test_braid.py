"""
@file        tests/test_braid.py
@purpose     The pipeline behaves: selection filters and cones compose, stubs
             bridge cut edges, the check-error gate holds, both strategies
             produce their promised sections, grouped falls back on group-level
             cycles with a warning, numbering is global, --dry summarizes, the
             cord is overridable, and the whole braid is deterministic across
             fresh loads.
@layer       tests
@tags        braid, selection, strategies, weave, determinism
@related     kumihimo/compile/braid.py (the pipeline under test),
             examples/apiguard (the fixture braided here)
@design      PLAN.md §4, queue item K8
"""

from pathlib import Path

import pytest

from kumihimo import KumihimoError, Plan, braid, export
from kumihimo.compile.select import select
from tests.conftest import PlanFactory

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "apiguard"


def test_selection_filters_compose_and_stub_cut_edges() -> None:
    plan = Plan.load(EXAMPLE)
    only_todo = select(plan, where={"status": "todo"})
    assert "pick-algorithm" not in only_todo.ids  # settled decision filtered out
    assert "rate-limit-core" in only_todo.ids
    assert "pick-algorithm" in only_todo.stubs  # but bridged as a stub

    cone = select(plan, until="rate-limit-core")
    assert set(cone.ids) == {"api-endpoints", "pick-algorithm", "rate-limit-core"}

    members = select(plan, in_="ship-guarded-api")
    assert set(members.ids) == {
        "api-endpoints",
        "headers-and-429",
        "rate-limit-core",
        "ship-guarded-api",
    }
    assert members.stubs == ["pick-algorithm"]


def test_selection_matching_nothing_errors() -> None:
    plan = Plan.load(EXAMPLE)
    with pytest.raises(KumihimoError, match="matches no nodes"):
        select(plan, where={"status": "no-such-status"})


def test_where_matches_inside_list_fields() -> None:
    plan = Plan.load(EXAMPLE)
    hits = select(plan, where={"acceptance": "429 + Retry-After on breach"})
    assert hits.ids == ["rate-limit-core"]


def test_braid_gates_on_check_errors(plan_dir: PlanFactory) -> None:
    root = plan_dir({"bad.md": "---\nkind: alien\n---\nBody.\n"})
    with pytest.raises(KumihimoError, match="check error"):
        braid(Plan.load(root))


def test_linear_is_one_section_grouped_is_shaped() -> None:
    plan = Plan.load(EXAMPLE)
    linear = braid(plan, strategy="linear")
    assert len(linear.sections) == 1
    assert linear.sections[0].title is None

    grouped = braid(plan, strategy="grouped")
    titles = [section.title for section in grouped.sections]
    assert titles == ["Context and prerequisites", "Ship guarded API", "Ungrouped"]
    assert grouped.sections[1].intro_id == "ship-guarded-api"
    assert grouped.sections[1].node_ids == [
        "api-endpoints",
        "rate-limit-core",
        "headers-and-429",
    ]
    assert grouped.sections[2].node_ids == ["per-org-quotas", "redis-outage"]


def test_numbering_is_global_and_intros_are_unnumbered() -> None:
    plan = Plan.load(EXAMPLE)
    result = braid(plan, strategy="grouped")
    assert result.order == [
        "pick-algorithm",
        "api-endpoints",
        "rate-limit-core",
        "headers-and-429",
        "per-org-quotas",
        "redis-outage",
    ]
    assert "ship-guarded-api" not in result.order  # section intro, not an item


def test_braid_text_is_deterministic_across_fresh_loads() -> None:
    first = braid(Plan.load(EXAMPLE)).text
    second = braid(Plan.load(EXAMPLE)).text
    assert first == second
    assert first.startswith("# Braid: API Guard\n")
    assert first.endswith("\n")
    assert "\n\n\n" not in first


def test_braid_carries_its_own_diagram_and_stub_lines() -> None:
    plan = Plan.load(EXAMPLE)
    text = braid(plan, where={"status": "todo"}).text
    assert "```mermaid" in text
    assert "Already in place, outside this braid: Rate-limit algorithm" in text
    assert "(already in place)" in text  # the After line marks the stub
    no_diagram = braid(plan, diagram=False).text
    assert "```mermaid" not in no_diagram


def test_dry_prints_order_without_rendering() -> None:
    plan = Plan.load(EXAMPLE)
    result = braid(plan, dry=True)
    assert result.text.startswith("braid order (grouped):")
    assert "[Ship guarded API]" in result.text
    assert "1. pick-algorithm" in result.text
    assert "Middleware on every authenticated route" not in result.text


def test_group_level_cycle_falls_back_to_linear_with_warning(plan_dir: PlanFactory) -> None:
    root = plan_dir(
        {
            "m1.md": "---\nkind: milestone\n---\nOne.\n",
            "m2.md": "---\nkind: milestone\n---\nTwo.\n",
            "a.md": "---\nkind: task\nin: [m1]\n---\nA.\n",
            "b.md": "---\nkind: task\nin: [m2]\nneeds: [a]\n---\nB.\n",
            "c.md": "---\nkind: task\nin: [m1]\nneeds: [b]\n---\nC.\n",
        }
    )
    result = braid(Plan.load(root), strategy="grouped")
    assert any("group-level" in warning for warning in result.warnings)
    assert len(result.sections) == 1
    assert "braid warning: group-level" in result.text


def test_unknown_strategy_names_the_known_ones() -> None:
    plan = Plan.load(EXAMPLE)
    with pytest.raises(KumihimoError, match="linear"):
        braid(plan, strategy="spiral")


def test_custom_cord_template_replaces_the_builtin(plan_dir: PlanFactory) -> None:
    manifest = (
        "format: 1\nplan: Corded\nkinds:\n  from: engineering\n"
        "compile:\n  strategy: linear\n  cord: cord.j2\n"
    )
    root = plan_dir(
        {
            "a.md": "---\nkind: task\nlinks: [b]\n---\nA.\n",
            "b.md": "---\nkind: task\nlinks: [a]\n---\nB.\n",
        },
        manifest=manifest,
    )
    (root / "cord.j2").write_bytes(b"{{ plan.name }} CUSTOM {{ sections|length }}\n")
    assert braid(Plan.load(root)).text == "Corded CUSTOM 1\n"


def test_plan_braid_sugar_and_exports() -> None:
    plan = Plan.load(EXAMPLE)
    assert plan.braid(strategy="linear") == braid(plan, strategy="linear").text
    mermaid_text = export.mermaid(plan)
    assert mermaid_text.startswith("graph LR")
    assert 'subgraph n_ship_guarded_api_g["Ship guarded API"]' in mermaid_text
    assert "n_pick_algorithm --> n_rate_limit_core" in mermaid_text
    assert "-. threatened-by .->" in mermaid_text
    dot_text = export.dot(plan)
    assert dot_text.startswith("digraph kumihimo {")
    assert "cluster_n_ship_guarded_api" in dot_text
