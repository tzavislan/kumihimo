"""
@file        kumihimo/compile/export.py
@purpose     The public export surface: a plan as Mermaid or DOT text, or as
             JSON Lines for offline retrieval indexing — exactly what
             `kumihimo export` and kumihimo.export.* hand out. Kumihimo never
             retrieves; jsonl is the corpus it exports (PLAN2 §3.7). jsonl is
             a machine feed and gates on check errors exactly like braid;
             mermaid/dot are diagnostic pictures and stay ungated on purpose
             — seeing a broken plan drawn is useful (docs/reference/cli.md).
@layer       compile
@tags        export, mermaid, dot, jsonl, rag, gate
@related     kumihimo/compile/diagram.py (generates the mermaid/dot text),
             kumihimo/compile/braid.py (gate_on_errors, shared with jsonl)
@design      PLAN.md §7.2, PLAN2.md §3.7
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from kumihimo.compile import diagram
from kumihimo.compile.braid import gate_on_errors
from kumihimo.core import kinds as kinds_module

if TYPE_CHECKING:
    from kumihimo.core.plan import Plan


def mermaid(plan: Plan) -> str:
    """The whole plan as a Mermaid graph.

    @purpose  Paste into any README; GitHub renders it natively. Ungated: a
              diagnostic picture is exactly what you want of a broken plan.
    """
    return diagram.mermaid(plan)


def dot(plan: Plan) -> str:
    """The whole plan as Graphviz DOT.

    @purpose  For real layout engines and SVG/PDF pipelines. Ungated, same
              reasoning as mermaid() above.
    """
    return diagram.dot(plan)


def jsonl(plan: Plan) -> str:
    """The plan as JSON Lines: one object per node, sorted by id.

    @purpose  The RAG ingestion shape (PLAN2 §3.7) — any indexer or embedding
              pipeline reads this offline; the library itself never fetches
              or retrieves. ensure_ascii and compact separators are pinned so
              the same plan always exports the same bytes, on every OS. Gated
              on check errors like braid (same message, same refusal) — a
              downstream indexer trusts this feed the way an agent trusts a
              braid; warnings alone don't block it.
    @tags     export, jsonl, rag, determinism, gate
    """
    gate_on_errors(plan)
    lines: list[str] = []
    for node_id in sorted(plan.nodes):
        node = plan.nodes[node_id]
        kind = plan.kinds.get(node.kind)
        effective = kinds_module.effective_fields(node, kind) if kind else dict(node.fields)
        record = {
            "id": node.id,
            "kind": node.kind,
            "title": node.title,
            "body": node.body,
            "effective": effective,
            "edges": {
                "needs": list(node.needs),
                "in": list(node.in_),
                "links": [{"to": link.to, "rel": link.rel} for link in node.links],
                "agents": list(node.agents),
                "skills": list(node.skills),
                "trains": list(node.trains),
            },
        }
        lines.append(json.dumps(record, ensure_ascii=True, separators=(",", ":")))
    return "".join(line + "\n" for line in lines)
