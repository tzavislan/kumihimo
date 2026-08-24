"""
@file        kumihimo/compile/diagram.py
@purpose     The graph as a picture, in text: Mermaid (embedded in braids and
             README-ready) and Graphviz DOT. Membership draws as subgraphs/
             clusters, needs as solid arrows, links as labeled dotted arrows,
             stubs as stadium shapes.
@layer       compile
@tags        mermaid, dot, diagram, export
@related     kumihimo/compile/weave.py (embeds the mermaid overview),
             kumihimo/compile/export.py (the CLI-facing wrappers)
@design      PLAN.md §4.3, §9 M2
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kumihimo.compile.select import Selection
    from kumihimo.core.plan import Plan

_SANITIZE = re.compile(r"[^A-Za-z0-9_]")


def _mid(node_id: str) -> str:
    """A Mermaid/DOT-safe identifier for a node id.

    @purpose  Slugs may contain '/' and '-'; diagram grammars want neither.
    """
    return "n_" + _SANITIZE.sub("_", node_id)


def mermaid(plan: Plan, selection: Selection | None = None) -> str:
    """The plan (or a selection of it) as a Mermaid graph.

    @purpose  The braid carries its own picture; GitHub renders this natively,
              so exports drop into any README.
    @tags     mermaid
    """
    ids = list(selection.ids) if selection else sorted(plan.nodes)
    stubs = list(selection.stubs) if selection else []
    chosen = set(ids)
    lines = ["graph LR"]
    groups: dict[str, list[str]] = {}
    ungrouped: list[str] = []
    for node_id in ids:
        node = plan.nodes[node_id]
        first_group = next((t for t in node.in_ if t in chosen), None)
        if first_group is not None and first_group != node_id:
            groups.setdefault(first_group, []).append(node_id)
        else:
            ungrouped.append(node_id)
    declared_in_group: set[str] = set()
    for group_id in sorted(groups):
        title = plan.nodes[group_id].title.replace('"', "'")
        lines.append(f'  subgraph {_mid(group_id)}_g["{title}"]')
        for member in groups[group_id]:
            lines.append(f'    {_mid(member)}["{member}"]')
            declared_in_group.add(member)
        lines.append("  end")
    for node_id in ungrouped:
        # Group nodes already appear as their subgraph; a floating duplicate
        # node would just be noise.
        if node_id not in declared_in_group and node_id not in groups:
            lines.append(f'  {_mid(node_id)}["{node_id}"]')
    for stub in stubs:
        lines.append(f'  {_mid(stub)}(["{stub} ✓"])')
    for node_id in ids:
        node = plan.nodes[node_id]
        for dep in node.needs:
            if dep in chosen or dep in stubs:
                lines.append(f"  {_mid(dep)} --> {_mid(node_id)}")
        for link in node.links:
            if link.to in chosen:
                lines.append(f"  {_mid(node_id)} -. {link.rel} .-> {_mid(link.to)}")
    return "\n".join(lines)


def dot(plan: Plan) -> str:
    """The whole plan as a Graphviz digraph with membership clusters.

    @purpose  For everything Mermaid isn't: real layout engines, SVG/PDF export.
    @tags     dot, graphviz
    """
    ids = sorted(plan.nodes)
    chosen = set(ids)
    lines = ["digraph kumihimo {", "  rankdir=LR;", '  node [shape=box, fontname="sans-serif"];']
    groups: dict[str, list[str]] = {}
    ungrouped: list[str] = []
    for node_id in ids:
        node = plan.nodes[node_id]
        first_group = next((t for t in node.in_ if t in chosen), None)
        if first_group is not None and first_group != node_id:
            groups.setdefault(first_group, []).append(node_id)
        else:
            ungrouped.append(node_id)
    for group_id in sorted(groups):
        title = plan.nodes[group_id].title.replace('"', "'")
        lines.append(f"  subgraph cluster_{_mid(group_id)} {{")
        lines.append(f'    label="{title}";')
        for member in groups[group_id]:
            lines.append(f'    {_mid(member)} [label="{member}"];')
        lines.append("  }")
    for node_id in ungrouped:
        lines.append(f'  {_mid(node_id)} [label="{node_id}"];')
    for node_id in ids:
        node = plan.nodes[node_id]
        for dep in node.needs:
            if dep in chosen:
                lines.append(f"  {_mid(dep)} -> {_mid(node_id)};")
        for link in node.links:
            if link.to in chosen:
                lines.append(
                    f'  {_mid(node_id)} -> {_mid(link.to)} [style=dotted, label="{link.rel}"];'
                )
    lines.append("}")
    return "\n".join(lines)
