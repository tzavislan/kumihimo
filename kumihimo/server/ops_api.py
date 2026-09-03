"""
@file        kumihimo/server/ops_api.py
@purpose     The editor's write path: one op envelope per gesture, validated by
             a discriminated union of pydantic models, digest-gated against
             concurrent edits, serialized by a single-writer lock, and executed
             through core.ops (positions and container collapse excepted —
             both are view state that goes straight to view.yaml, never a
             node file). Every apply() also computes that op's inverse from
             state read immediately before it runs (K32): a full envelope the
             client can POST back verbatim to undo it, the node digest(s) it
             preconditions on (so a later external edit grays the trail entry
             instead of silently mis-undoing), and one human-readable label.
             remove_node's inverse (K45) is a restore_node envelope carrying
             the exact prior file bytes, read before the file is deleted, and
             the prior view.yaml position when it had one; restore_node's own
             inverse is in turn a remove_node envelope, the same shape
             add_node's already is. The one honest null left is set_positions
             on a node's first-ever placement — no prior position exists to
             restore.
@layer       server
@tags        ops-envelope, digests, single-writer, view-layout, containers,
             mentions, undo, inverse-ops, restore
@related     kumihimo/core/ops.py (every mutation lands there),
             kumihimo/server/app.py (mounts apply() at POST /api/ops, merges
             OpOutcome's fields into the response payload),
             kumihimo/server/payload.py (file_digest, the concurrency token —
             also the inverse's precondition unit; also reads `collapsed`
             back out of view.yaml for the payload),
             frontend/src/useUndoTrail.ts (the client-side trail this feeds)
@design      PLAN.md §5.2-5.3, PLAN2.md §2.5 Undo trail, §5 risk 4, queue
             item K45
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
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
              Its own inverse (K45) is a restore_node envelope — see
              OpOutcome's docstring for the full reasoning, including why its
              preconditions stay empty.
    """

    op: Literal["remove_node"]
    node_id: str
    force: bool = False


class RestoreNodeOp(_Op):
    """Envelope for ops.restore_node (K45).

    @purpose  remove_node's real inverse: recreates the file from the exact
              bytes remove_node read just before deleting it. No base_digest
              — there is no file yet to gate on; the op's own already-exists
              refusal is what stops a stale replay instead. `position`
              restores the node's prior view.yaml layout entry when it had
              one.
    """

    op: Literal["restore_node"]
    node_id: str
    content: str
    position: tuple[int, int] | None = None


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
    | RestoreNodeOp
    | LinkOp
    | UnlinkOp
    | RenameNodeOp
    | SetPositionsOp
    | SetCollapsedOp,
    Field(discriminator="op"),
]


@dataclass
class OpOutcome:
    """What one applied op hands back for the undo trail (K32).

    @purpose  `inverse` is a full OpRequest-shaped envelope (JSON, by alias)
              the client can POST back to `/api/ops` verbatim to undo this
              op, or None when the op is honestly not reversible this way —
              today that's only set_positions on a node's first-ever
              placement, where no prior position exists to restore. Every op
              that touches exactly one existing node file executes while
              already holding that node's own digest check, so the inverse's
              `base_digest` and this same value in `preconditions` are always
              the SAME post-op digest: undoing an undo works for exactly the
              reason applying the original op did. Three documented
              exceptions to that digest-precondition pattern: `preconditions`
              is empty for set_positions/set_collapsed, since those touch
              view.yaml, which carries no digest of its own in this contract
              (forward set_positions/set_collapsed have no digest gate
              either, today); and empty for remove_node (K45) too, for a
              different reason — its restore_node inverse's own real
              precondition is honestly "this id is absent," a state today's
              frontend trail matcher (useUndoTrail.ts's {id, digest}
              comparison, where a missing id reads as JS `undefined`, never
              a distinguishable "must be absent") cannot express without a
              frontend edit this round didn't make. In all three cases the
              trail entry stays enabled unconditionally; for remove_node's
              restore, restore_node's own already-exists refusal is what
              actually stops a stale click, surfacing as the ordinary error
              notice instead of a silently wrong undo. `label` is one human
              sentence for the trail.
    """

    inverse: dict[str, Any] | None
    preconditions: list[dict[str, str]]
    label: str


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


def _node_path(root: Path, node_id: str) -> Path:
    """The on-disk path for a node id, matching store's own layout.

    @purpose  One spelling of "where does this id's file live", shared by
              digest gating and the K32 inverse/precondition computation.
    """
    return root / store.NODES_DIR / Path(node_id + ".md")


def _precondition(node_id: str, digest: str) -> list[dict[str, str]]:
    """One {id, digest} precondition list — the common single-node case.

    @purpose  Every op that touches exactly one node file (all but
              set_positions/set_collapsed) preconditions its inverse on that
              same node's post-op digest.
    """
    return [{"id": node_id, "digest": digest}]


def _prior_position(root: Path, node_id: str) -> list[int] | None:
    """This id's current view.yaml position, as [x, y], or None if it has none.

    @purpose  RemoveNodeOp's restore-inverse (K45) needs the position read
              before the file — and its layout entry — are gone.
    """
    view = store.load_view(root)
    layout = view.get("layout") if view is not None else None
    if not isinstance(layout, dict):
        return None
    entry = layout.get(node_id)
    if isinstance(entry, dict) and "x" in entry and "y" in entry:
        return [int(entry["x"]), int(entry["y"])]
    return None


def _edge_key_target(
    needs: str | None,
    in_: str | None,
    to: str | None,
    agents: str | None,
    skills: str | None,
    trains: str | None,
) -> tuple[str, str]:
    """The (json-key, target) pair among link/unlink's six optional kwargs.

    @purpose  One spelling of "which edge kwarg was actually given" for the
              inverse builders below — core.ops.link/unlink already enforce
              exactly one is set, by the time this runs.
    """
    for key, value in (
        ("needs", needs),
        ("in", in_),
        ("to", to),
        ("agents", agents),
        ("skills", skills),
        ("trains", trains),
    ):
        if value is not None:
            return key, value
    raise KumihimoError("give exactly one of needs=, in_=, to=, agents=, skills=, or trains=")


def _edge_sentence(key: str, src: str, target: str, rel: str | None = None) -> str:
    """ "A needs B" / "A is in B" / "A links B (rel)" / "A mentions B (key)".

    @purpose  Mirrors frontend/src/edges.ts's edgeSentence in words, for the
              K32 undo trail's own link/unlink labels — ids, not titles,
              since the server has no reason to load a second node's title
              just to name an edge.
    """
    if key == "needs":
        return f"{src} needs {target}"
    if key == "in":
        return f"{src} is in {target}"
    if key == "to":
        return f"{src} links {target}" + (f" ({rel})" if rel and rel != "see-also" else "")
    return f"{src} mentions {target} ({key})"


def _update_inverse(
    request: UpdateNodeOp, prior: store.NodeRecord, digest: str
) -> tuple[dict[str, Any], str]:
    """The inverse update_node envelope plus a human label, from before-state.

    @purpose  Restores every part this update actually changed, byte-for-
              byte: kind/title/body/priority when touched-and-different, each
              set_fields entry that changed value (NodeForm.tsx's Save resends
              every visible field, changed or not — an unchanged one would
              otherwise pollute both the inverse and the label with a no-op
              "x -> x" clause), each unset_fields entry (always meaningful:
              update_node itself already refuses to unset a field that wasn't
              there). A field this op newly created (absent from `prior`)
              gets unset back out rather than restored to a fabricated value.
    @tags     undo, update-node
    """
    inverse: dict[str, Any] = {
        "op": "update_node",
        "node_id": request.node_id,
        "base_digest": digest,
    }
    clauses: list[str] = []
    if request.kind is not None and request.kind != prior.node.kind:
        inverse["kind"] = prior.node.kind
        clauses.append(f"kind: {prior.node.kind} → {request.kind}")
    if request.title is not None and request.title != prior.node.title:
        inverse["title"] = prior.node.title
        clauses.append(f"title: {prior.node.title!r} → {request.title!r}")
    if request.body is not None and request.body != prior.node.body:
        inverse["body"] = prior.node.body
        clauses.append("body edited")
    if request.priority is not None and request.priority != prior.node.priority:
        inverse["priority"] = prior.node.priority
        clauses.append(f"priority: {prior.node.priority} → {request.priority}")
    set_back: dict[str, Any] = {}
    unset_back: list[str] = []
    for name, value in request.set_fields.items():
        if name not in prior.node.fields:
            unset_back.append(name)
            clauses.append(f"{name}: (none) → {value}")
        elif prior.node.fields[name] != value:
            old = prior.node.fields[name]
            set_back[name] = old
            clauses.append(f"{name}: {old} → {value}")
        # else: resent unchanged (NodeForm.tsx resends every visible field) —
        # nothing to restore, nothing worth a clause.
    for name in request.unset_fields:
        old = prior.node.fields.get(name)
        set_back[name] = old
        clauses.append(f"{name} removed (was {old})")
    if set_back:
        inverse["set_fields"] = set_back
    if unset_back:
        inverse["unset_fields"] = unset_back
    # The "set X key: old -> new" shorthand only reads naturally when the
    # sole clause actually IS a "key: value" fragment — "set a body edited"
    # would not, so a lone body/kind-unset-shaped clause without one falls
    # through to the general "update X: ..." phrasing instead.
    if len(clauses) == 1 and ": " in clauses[0]:
        label = f"set {request.node_id} {clauses[0]}"
    elif clauses:
        label = f"update {request.node_id}: " + "; ".join(clauses)
    else:
        label = f"update {request.node_id}"
    return inverse, label


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


def apply(root: Path, request: OpRequest) -> OpOutcome:
    """Execute one validated op under the single-writer lock; hand back its
    inverse for the undo trail (K32).

    @purpose  The only write door the editor has; everything semantic goes
              through core.ops so the CLI, MCP, and editor can never diverge.
              Before-state for the inverse is read here, at the same moment
              _check_digest already reads the file (or, for unlink's `to=`
              case, via one extra Plan.load) — no new race, since the whole
              body runs under _WRITE_LOCK.
    @tags     single-writer, ops, undo
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
            digest = file_digest(_node_path(root, request.node_id))
            inverse: dict[str, Any] = {
                "op": "remove_node",
                "node_id": request.node_id,
                "base_digest": digest,
            }
            return OpOutcome(
                inverse, _precondition(request.node_id, digest), f"add {request.node_id}"
            )

        elif isinstance(request, UpdateNodeOp):
            _check_digest(root, request.node_id, request.base_digest)
            prior_record = Plan.load(root).records.get(request.node_id)
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
            digest = file_digest(_node_path(root, request.node_id))
            if prior_record is None:
                # Unreachable in practice — ops.update_node above would have
                # raised "no node" first — but honest rather than fabricated
                # prior values if some future caller ever gets here anyway.
                return OpOutcome(None, [], f"update {request.node_id}")
            inverse, label = _update_inverse(request, prior_record, digest)
            return OpOutcome(inverse, _precondition(request.node_id, digest), label)

        elif isinstance(request, RemoveNodeOp):
            _check_digest(root, request.node_id, request.base_digest)
            # Before-state for the restore inverse (K45), read the same way
            # store.py's own load does — raw bytes decoded, no universal-
            # newline translation — so a CRLF file's inverse carries the
            # exact bytes remove_node is about to delete, not a mangled copy.
            prior_path = _node_path(root, request.node_id)
            prior_content: str | None = None
            if prior_path.is_file():
                prior_content = prior_path.read_bytes().decode("utf-8")
            prior_position = _prior_position(root, request.node_id)
            ops.remove_node(root, request.node_id, force=request.force, actor="editor")
            label = f"remove {request.node_id}"
            if prior_content is None:
                # Unreachable in practice — ops.remove_node above would have
                # raised "no node" first — but honest rather than a
                # fabricated restore envelope if some future caller (no
                # base_digest given, so _check_digest never confirmed the
                # file existed) ever gets here anyway.
                return OpOutcome(None, [], label)
            inverse = {
                "op": "restore_node",
                "node_id": request.node_id,
                "content": prior_content,
            }
            if prior_position is not None:
                inverse["position"] = prior_position
            # preconditions stays [] — see OpOutcome's own docstring for why
            # "this id is absent" can't be expressed as a {id, digest} check
            # against today's frontend trail matcher without a frontend
            # edit. The entry is enabled unconditionally; restore_node's own
            # already-exists refusal catches a stale click instead.
            return OpOutcome(inverse, [], label)

        elif isinstance(request, RestoreNodeOp):
            ops.restore_node(
                root,
                request.node_id,
                request.content,
                position=request.position,
                actor="editor",
            )
            digest = file_digest(_node_path(root, request.node_id))
            inverse = {
                "op": "remove_node",
                "node_id": request.node_id,
                "base_digest": digest,
            }
            label = f"restore {request.node_id}"
            return OpOutcome(inverse, _precondition(request.node_id, digest), label)

        elif isinstance(request, LinkOp):
            _check_digest(root, request.src, request.base_digest)
            key, target = _edge_key_target(
                request.needs,
                request.in_,
                request.to,
                request.agents,
                request.skills,
                request.trains,
            )
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
            digest = file_digest(_node_path(root, request.src))
            inverse = {"op": "unlink", "src": request.src, "base_digest": digest, key: target}
            label = f"link: {_edge_sentence(key, request.src, target, request.rel)}"
            return OpOutcome(inverse, _precondition(request.src, digest), label)

        elif isinstance(request, UnlinkOp):
            _check_digest(root, request.src, request.base_digest)
            key, target = _edge_key_target(
                request.needs,
                request.in_,
                request.to,
                request.agents,
                request.skills,
                request.trains,
            )
            # Only `to=` needs before-state: the removed link's own `rel`
            # (default "see-also" when it was a plain string entry) is what
            # the inverse must recreate — every other key's inverse is just
            # the same (key, target) pair, no extra state to lose.
            prior_rel = "see-also"
            if key == "to":
                before_node = Plan.load(root).nodes.get(request.src)
                found = (
                    next((link for link in before_node.links if link.to == target), None)
                    if before_node
                    else None
                )
                if found is not None:
                    prior_rel = found.rel
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
            digest = file_digest(_node_path(root, request.src))
            inverse = {"op": "link", "src": request.src, "base_digest": digest, key: target}
            label_rel = prior_rel if key == "to" else None
            if key == "to":
                inverse["rel"] = prior_rel
            label = f"unlink: {_edge_sentence(key, request.src, target, label_rel)}"
            return OpOutcome(inverse, _precondition(request.src, digest), label)

        elif isinstance(request, RenameNodeOp):
            _check_digest(root, request.old, request.base_digest)
            ops.rename_node(root, request.old, request.new, actor="editor")
            digest = file_digest(_node_path(root, request.new))
            inverse = {
                "op": "rename_node",
                "old": request.new,
                "new": request.old,
                "base_digest": digest,
            }
            label = f"rename {request.old} → {request.new}"
            return OpOutcome(inverse, _precondition(request.new, digest), label)

        elif isinstance(request, SetPositionsOp):
            # No digest concept for view.yaml (forward set_positions itself
            # carries no digest gate either) — preconditions stays empty, so
            # a move's trail entry is always enabled. Only ids that already
            # had an explicit prior position can be restored; an id placed
            # for the first time has no server-known "before" (its old spot
            # was purely elk's client-side auto-layout guess) and is simply
            # left out of the inverse rather than restored to a fiction.
            prior_view = store.load_view(root)
            prior_layout = prior_view.get("layout") if prior_view is not None else None
            restored: dict[str, dict[str, int]] = {}
            if isinstance(prior_layout, dict):
                for node_id in request.positions:
                    entry = prior_layout.get(node_id)
                    if isinstance(entry, dict) and "x" in entry and "y" in entry:
                        restored[node_id] = {"x": int(entry["x"]), "y": int(entry["y"])}
            _set_positions(root, request.positions)
            label = f"move {', '.join(sorted(request.positions))}"
            move_inverse = {"op": "set_positions", "positions": restored} if restored else None
            return OpOutcome(move_inverse, [], label)

        else:
            # SetCollapsedOp. Same no-digest reasoning as positions above.
            prior_view = store.load_view(root)
            prior_raw = prior_view.get("collapsed") if prior_view is not None else None
            prior_collapsed = (
                sorted({str(item) for item in prior_raw}) if isinstance(prior_raw, list) else []
            )
            _set_collapsed(root, request.collapsed)
            added = sorted(set(request.collapsed) - set(prior_collapsed))
            removed = sorted(set(prior_collapsed) - set(request.collapsed))
            if added:
                label = f"collapse {', '.join(added)}"
            elif removed:
                label = f"expand {', '.join(removed)}"
            else:
                label = "collapse: unchanged"
            collapse_inverse = {"op": "set_collapsed", "collapsed": prior_collapsed}
            return OpOutcome(collapse_inverse, [], label)
