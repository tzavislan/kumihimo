"""
@file        tests/test_graph.py
@purpose     The ordering invariant, executable: braid_order is identical under
             any insertion order, priority then id breaks ties, cycles are named
             as exact paths (self-loops included), and cones walk the right
             directions.
@layer       tests
@tags        topo-sort, determinism, cycles, cones
@related     kumihimo/core/graph.py (under test)
@design      PLAN.md §4.1 step 2, queue item K3
"""

import pytest

from kumihimo.core.errors import CycleError, KumihimoError
from kumihimo.core.graph import ancestors, braid_order, descendants, find_cycle
from kumihimo.core.model import Node


def build(
    *specs: tuple[str, list[str]], priorities: dict[str, int] | None = None
) -> dict[str, Node]:
    priorities = priorities or {}
    return {
        node_id: Node(id=node_id, kind="task", needs=needs, priority=priorities.get(node_id, 0))
        for node_id, needs in specs
    }


DIAMOND = (("d", ["b", "c"]), ("b", ["a"]), ("c", ["a"]), ("a", []))


def test_order_ignores_insertion_order() -> None:
    forward = build(*DIAMOND)
    backward = build(*reversed(DIAMOND))
    assert braid_order(forward) == braid_order(backward) == ["a", "b", "c", "d"]


def test_ties_break_by_priority_then_id() -> None:
    nodes = build(("a", []), ("b", []), ("c", []), priorities={"c": 5})
    assert braid_order(nodes) == ["c", "a", "b"]


def test_priority_never_overrides_dependencies() -> None:
    nodes = build(("late", []), ("early", ["late"]), priorities={"early": 99})
    assert braid_order(nodes) == ["late", "early"]


def test_dangling_needs_do_not_block_ordering() -> None:
    nodes = build(("a", ["ghost"]), ("b", ["a"]))
    assert braid_order(nodes) == ["a", "b"]


def test_cycle_raises_with_exact_path() -> None:
    nodes = build(("a", ["c"]), ("b", ["a"]), ("c", ["b"]), ("solo", []))
    with pytest.raises(CycleError) as excinfo:
        braid_order(nodes)
    assert excinfo.value.nodes == ["a", "c", "b"]
    assert "a -> c -> b -> a" in str(excinfo.value)


def test_self_loop_is_a_cycle() -> None:
    nodes = build(("a", ["a"]))
    with pytest.raises(CycleError) as excinfo:
        braid_order(nodes)
    assert excinfo.value.nodes == ["a"]


def test_find_cycle_none_on_dag() -> None:
    assert find_cycle(build(*DIAMOND)) is None


def test_cones_walk_the_right_directions() -> None:
    nodes = build(*DIAMOND)
    assert ancestors(nodes, "d") == {"a", "b", "c"}
    assert descendants(nodes, "a") == {"b", "c", "d"}
    assert ancestors(nodes, "a") == set()
    assert descendants(nodes, "d") == set()


def test_cone_on_unknown_id_raises_clean() -> None:
    with pytest.raises(KumihimoError, match="ghost"):
        ancestors(build(("a", [])), "ghost")
