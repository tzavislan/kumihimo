"""
@file        kumihimo/server/payload.py
@purpose     The one JSON shape the canvas consumes: plan meta, every node with
             raw and effective fields plus body, current findings, the view
             layout, and the kind definitions the editor's forms will need.
@layer       server
@tags        payload, json, canvas-contract
@related     kumihimo/server/app.py (serves this over GET and WebSocket),
             frontend/src/types.ts (the TypeScript mirror of this shape)
@design      PLAN.md §5.2
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kumihimo.core import kinds as kinds_module
from kumihimo.core import store
from kumihimo.core.plan import Plan


def file_digest(path: Path) -> str:
    """The sha256 of a file's bytes, hex.

    @purpose  The optimistic-concurrency token: ops carry the digest they were
              based on, and a stale one is rejected instead of clobbered.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_payload(root: Path) -> dict[str, Any]:
    """Everything the canvas needs, in one load.

    @purpose  The filesystem is the bus: this is rebuilt from disk on every
              request and every change event, never cached, so the browser can
              only ever see what a cold reader would.
    @tags     payload, files-as-truth
    """
    plan = Plan.load(root)
    findings = plan.check()
    view = store.load_view(root)
    layout_raw = view.get("layout") if view is not None else None
    layout: dict[str, dict[str, int]] = {}
    if isinstance(layout_raw, dict):
        for node_id, position in layout_raw.items():
            if isinstance(position, dict) and "x" in position and "y" in position:
                layout[str(node_id)] = {"x": int(position["x"]), "y": int(position["y"])}
    nodes = []
    for node_id in sorted(plan.nodes):
        node = plan.nodes[node_id]
        kind = plan.kinds.get(node.kind)
        effective = kinds_module.effective_fields(node, kind) if kind else dict(node.fields)
        nodes.append(
            {
                "digest": file_digest(plan.records[node_id].path),
                "id": node.id,
                "kind": node.kind,
                "title": node.title,
                "needs": list(node.needs),
                "in": list(node.in_),
                "links": [{"to": link.to, "rel": link.rel} for link in node.links],
                "priority": node.priority,
                "fields": dict(node.fields),
                "effective": effective,
                "body": node.body,
            }
        )
    return {
        "plan": plan.manifest.plan,
        "description": plan.manifest.description,
        "strategy": plan.manifest.compile.strategy,
        "kinds": {
            name: {
                "color": kind.color,
                "fields": {
                    field_name: spec.model_dump() for field_name, spec in kind.fields.items()
                },
            }
            for name, kind in sorted(plan.kinds.items())
        },
        "nodes": nodes,
        "findings": [finding.model_dump() for finding in findings],
        "layout": layout,
    }
