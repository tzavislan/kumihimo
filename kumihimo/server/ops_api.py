"""
@file        kumihimo/server/ops_api.py
@purpose     The editor's write path: one op envelope per gesture, validated by
             a discriminated union of pydantic models, digest-gated against
             concurrent edits, serialized by a single-writer lock, and executed
             through core.ops (positions and container collapse excepted —
             both are view state that goes straight to view.yaml, never a
             node file).
@layer       server
@tags        ops-envelope, digests, single-writer, view-layout, containers,
             mentions
@related     kumihimo/core/ops.py (every mutation lands there),
             kumihimo/server/app.py (mounts apply() at POST /api/ops),
             kumihimo/server/payload.py (file_digest, the concurrency token;
             also reads `collapsed` back out of view.yaml for the payload)
@design      PLAN.md §5.2-5.3
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from kumihimo.core import ops, store
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan
from kumihimo.server.payload import file_digest

_WRITE_LOCK = threading.Lock()


class StaleDigestError(KumihimoError):
    """The file changed since the client last saw it.

    @purpose  Distinguishable from ordinary op errors so the API can answer 409
              and the client knows to refresh rather than apologize.
    """


class _Op(BaseModel):
    """Shared shape of every op envelope.

    @purpose  One place for the extra="forbid" discipline and the digest field.
    """

    model_config = ConfigDict(extra="forbid")

    base_digest: str | None = None


class AddNodeOp(_Op):
    """Envelope for ops.add_node.

    @purpose  Creating a node; no base_digest — there is no file yet.
    """

    op: Literal["add_node"]
    node_id: str
    kind: str
    title: str | None = None
    body: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    needs: list[str] = Field(default_factory=list)
    in_: list[str] = Field(default_factory=list, alias="in")


class UpdateNodeOp(_Op):
    """Envelope for ops.update_node.

    @purpose  The form-save gesture; digest-gated.
    """

    op: Literal["update_node"]
    node_id: str
    kind: str | None = None
    title: str | None = None
    body: str | None = None
    priority: int | None = None
    set_fields: dict[str, Any] = Field(default_factory=dict)
    unset_fields: list[str] = Field(default_factory=list)


class RemoveNodeOp(_Op):
    """Envelope for ops.remove_node.

    @purpose  Deletion; digest-gated so a stale delete cannot take fresh work.
    """

    op: Literal["remove_node"]
    node_id: str
    force: bool = False


class LinkOp(_Op):
    """Envelope for ops.link.

    @purpose  The drawn-edge gesture (needs/in/links) and the sidebar's chip-
              editor gesture (agents/skills/trains mentions, K30); digest
              gates the source file. Six optional targets, mirroring core
              ops.link's own exactly-one-of contract — this envelope just
              carries all of them through and lets core enforce it.
    """

    op: Literal["link"]
    src: str
    needs: str | None = None
    in_: str | None = Field(default=None, alias="in")
    to: str | None = None
    rel: str = "see-also"
    agents: str | None = None
    skills: str | None = None
    trains: str | None = None


class UnlinkOp(_Op):
    """Envelope for ops.unlink.

    @purpose  Edge deletion, mentions included (K30); digest gates the
              source file.
    """

    op: Literal["unlink"]
    src: str
    needs: str | None = None
    in_: str | None = Field(default=None, alias="in")
    to: str | None = None
    agents: str | None = None
    skills: str | None = None
    trains: str | None = None


class RenameNodeOp(_Op):
    """Envelope for ops.rename_node.

    @purpose  Identity change with referrer fixup; digest gates the old file.
    """

    op: Literal["rename_node"]
    old: str
    new: str


class SetPositionsOp(_Op):
    """Positions into view.yaml — layout, never semantics.

    @purpose  Drag-end writes coordinates to the sidecar only; a pure layout
              change must never touch a node file.
    """

    op: Literal["set_positions"]
    positions: dict[str, dict[str, int]]


class SetCollapsedOp(_Op):
    """Collapsed-container ids into view.yaml — view state, never semantics.

    @purpose  Mirrors SetPositionsOp (PLAN2.md §2.3 lens 1): the collapse
              toggle writes a sidecar list only, next to `layout`, never a
              node file. A fresh list, not a delta — the client always sends
              the whole collapsed set it wants persisted.
    """

    op: Literal["set_collapsed"]
    collapsed: list[str]


OpRequest = Annotated[
    AddNodeOp
    | UpdateNodeOp
    | RemoveNodeOp
    | LinkOp
    | UnlinkOp
    | RenameNodeOp
    | SetPositionsOp
    | SetCollapsedOp,
    Field(discriminator="op"),
]


def _check_digest(root: Path, node_id: str, base_digest: str | None) -> None:
    """Reject the op when the client's file snapshot is stale.

    @purpose  The whole conflict policy: compare, and 409 instead of clobber.
              No digest supplied means the caller opted out (CLI-grade trust).
    """
    if base_digest is None:
        return
    path = root / store.NODES_DIR / Path(node_id + ".md")
    if not path.is_file():
        raise KumihimoError(f"no node '{node_id}'")
    current = file_digest(path)
    if current != base_digest:
        raise StaleDigestError(f"'{node_id}' changed since you loaded it; refresh and re-apply")


def _set_positions(root: Path, positions: dict[str, dict[str, int]]) -> None:
    """Write coordinates into view.yaml, keys sorted, values flow-style.

    @purpose  A layout shuffle stays a two-line diff: ints only, stable order,
              {x: .., y: ..} inline.
    """
    view = store.load_view(root)
    if view is None:
        view = CommentedMap()
    layout = view.get("layout")
    if not isinstance(layout, dict):
        layout = CommentedMap()
        view["layout"] = layout
    for node_id, position in positions.items():
        entry = CommentedMap()
        entry["x"] = int(position.get("x", 0))
        entry["y"] = int(position.get("y", 0))
        entry.fa.set_flow_style()
        layout[node_id] = entry
    ordered = CommentedMap()
    for node_id in sorted(layout):
        ordered[node_id] = layout[node_id]
    view["layout"] = ordered
    store.save_view(root, view)


def _set_collapsed(root: Path, collapsed: list[str]) -> None:
    """Write the collapsed-container id list into view.yaml, sorted, flow.

    @purpose  A container's fold state is layout, not semantics — same
              sidecar rule as positions. The key is dropped entirely rather
              than persisted empty, so an all-expanded plan's view.yaml stays
              exactly as clean as before this op existed. Every id is
              validated first: a stray or mistyped id would otherwise fold a
              plain leaf card into an unrenderable "container" client-side —
              400 with a message naming the actual problem beats a canvas
              that just goes quiet.
    """
    plan = Plan.load(root)
    container_ids = {
        target for node in plan.nodes.values() for target in node.in_ if target in plan.nodes
    }
    for node_id in collapsed:
        if node_id not in plan.nodes:
            raise KumihimoError(f"no node '{node_id}'")
        if node_id not in container_ids:
            raise KumihimoError(f"'{node_id}' is not a container (no node names it in `in`)")
    view = store.load_view(root)
    if view is None:
        view = CommentedMap()
    ids = sorted(set(collapsed))
    if not ids:
        view.pop("collapsed", None)
    else:
        seq = CommentedSeq(ids)
        seq.fa.set_flow_style()
        view["collapsed"] = seq
    store.save_view(root, view)


def apply(root: Path, request: OpRequest) -> None:
    """Execute one validated op under the single-writer lock.

    @purpose  The only write door the editor has; everything semantic goes
              through core.ops so the CLI, MCP, and editor can never diverge.
    @tags     single-writer, ops
    """
    with _WRITE_LOCK:
        if isinstance(request, AddNodeOp):
            ops.add_node(
                root,
                request.node_id,
                request.kind,
                title=request.title,
                body=request.body,
                fields=request.fields,
                needs=tuple(request.needs),
                in_=tuple(request.in_),
                actor="editor",
            )
        elif isinstance(request, UpdateNodeOp):
            _check_digest(root, request.node_id, request.base_digest)
            ops.update_node(
                root,
                request.node_id,
                kind=request.kind,
                title=request.title,
                body=request.body,
                priority=request.priority,
                set_fields=request.set_fields or None,
                unset_fields=tuple(request.unset_fields),
                actor="editor",
            )
        elif isinstance(request, RemoveNodeOp):
            _check_digest(root, request.node_id, request.base_digest)
            ops.remove_node(root, request.node_id, force=request.force, actor="editor")
        elif isinstance(request, LinkOp):
            _check_digest(root, request.src, request.base_digest)
            ops.link(
                root,
                request.src,
                needs=request.needs,
                in_=request.in_,
                to=request.to,
                rel=request.rel,
                agents=request.agents,
                skills=request.skills,
                trains=request.trains,
                actor="editor",
            )
        elif isinstance(request, UnlinkOp):
            _check_digest(root, request.src, request.base_digest)
            ops.unlink(
                root,
                request.src,
                needs=request.needs,
                in_=request.in_,
                to=request.to,
                agents=request.agents,
                skills=request.skills,
                trains=request.trains,
                actor="editor",
            )
        elif isinstance(request, RenameNodeOp):
            _check_digest(root, request.old, request.base_digest)
            ops.rename_node(root, request.old, request.new, actor="editor")
        elif isinstance(request, SetPositionsOp):
            _set_positions(root, request.positions)
        else:
            _set_collapsed(root, request.collapsed)
