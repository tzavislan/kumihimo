"""
@file        kumihimo/core/ops.py
@purpose     The one mutation path (invariant 1): add, update, link, unlink,
             rename, remove — each loads fresh from disk, edits the record's
             live frontmatter map so comments survive, refuses structural
             nonsense (dangling targets, cycles, id collisions) with clean
             errors, saves atomically, and returns the reloaded result.
@layer       core
@tags        ops, mutations, invariant-1, referrer-fixup
@related     kumihimo/core/store.py (the records and saves),
             kumihimo/core/graph.py (the cycle guard on link),
             kumihimo/core/plan.py (Plan.load used before and after)
@design      PLAN.md §7.1 invariant 1, queue item K5
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedSeq

from kumihimo.core import graph, store
from kumihimo.core.errors import KumihimoError
from kumihimo.core.model import RESERVED_KEYS, SLUG_RE, Node
from kumihimo.core.plan import Plan
from kumihimo.core.store import NodeRecord


def _require_slug(node_id: str) -> None:
    """Reject ids that break the filename rules before they reach disk.

    @purpose  The slug rule is load-time validation for hand-written files but a
              hard precondition for ops — tools never create bad ids.
    """
    if not SLUG_RE.match(node_id):
        message = f"'{node_id}' is not a valid id (lowercase a-z0-9-, / for namespaces)"
        raise KumihimoError(message)


def _record(plan: Plan, node_id: str) -> NodeRecord:
    """A node's record, or the standard missing-node error.

    @purpose  One phrasing for "that node doesn't exist" across every op.
    """
    record = plan.records.get(node_id)
    if record is None:
        raise KumihimoError(f"no node '{node_id}' in {plan.root.name}")
    return record


def _require_exists(plan: Plan, node_id: str, why: str) -> None:
    """Refuse an edge to a target that isn't in the plan.

    @purpose  Ops are strict where hand-editing is free: a tool that writes a
              dangling reference is a bug, a human doing it is a finding.
    """
    if node_id not in plan.records:
        raise KumihimoError(f"{why} target '{node_id}' does not exist")


def _flow_seq(values: list[str]) -> CommentedSeq:
    """A [a, b] style sequence for edge lists.

    @purpose  Matches the documented format and keeps one-line diffs.
    """
    seq = CommentedSeq(values)
    seq.fa.set_flow_style()
    return seq


def _list_add(record: NodeRecord, key: str, value: str) -> None:
    """Append a value to a scalar-or-list frontmatter key.

    @purpose  `needs: a` and `needs: [a, b]` both grow correctly.
    """
    current = record.fm.get(key)
    if current is None:
        record.fm[key] = _flow_seq([value])
    elif isinstance(current, str):
        record.fm[key] = _flow_seq([current, value])
    else:
        current.append(value)


def _list_remove(record: NodeRecord, key: str, value: str) -> None:
    """Remove a value from a scalar-or-list key, dropping the key when emptied.

    @purpose  Unlink leaves files as tidy as if the edge had never existed.
    """
    current = record.fm.get(key)
    if isinstance(current, str):
        if current != value:
            raise KumihimoError(f"'{record.node.id}' has no {key} entry '{value}'")
        del record.fm[key]
        return
    if not isinstance(current, list) or value not in current:
        raise KumihimoError(f"'{record.node.id}' has no {key} entry '{value}'")
    current.remove(value)
    if len(current) == 0:
        del record.fm[key]


def _save_and_reload(root: Path, *records: NodeRecord) -> Plan:
    """Persist the given records and load the plan fresh.

    @purpose  Files are the truth: every op's return value is what a cold reader
              would now see, not what memory hopes is there.
    """
    for record in records:
        record.dirty = True
        store.save_record(record)
    return Plan.load(root)


def add_node(
    root: Path,
    node_id: str,
    kind: str,
    *,
    title: str | None = None,
    body: str = "",
    fields: dict[str, Any] | None = None,
    needs: tuple[str, ...] = (),
    in_: tuple[str, ...] = (),
) -> Node:
    """Create a node file with canonical frontmatter and return it.

    @purpose  The only way tools bring a node into existence; every edge target
              must already exist and the id must be free.
    @tags     ops, add
    """
    plan = Plan.load(root)
    _require_slug(node_id)
    lowered = {existing.lower() for existing in plan.records}
    if node_id.lower() in lowered:
        raise KumihimoError(f"node '{node_id}' already exists")
    if kind not in plan.kinds:
        known = ", ".join(sorted(plan.kinds)) or "none defined"
        raise KumihimoError(f"unknown kind '{kind}' (this plan defines: {known})")
    for target in (*needs, *in_):
        _require_exists(plan, target, "edge")
    node = Node(
        id=node_id,
        kind=kind,
        title=title or "",
        needs=list(needs),
        in_=list(in_),
        fields=fields or {},
        body=body,
    )
    record = store.new_record(plan.root, node)
    store.save_record(record)
    return Plan.load(root).node(node_id)


def update_node(
    root: Path,
    node_id: str,
    *,
    kind: str | None = None,
    title: str | None = None,
    body: str | None = None,
    priority: int | None = None,
    set_fields: dict[str, Any] | None = None,
    unset_fields: tuple[str, ...] = (),
) -> Node:
    """Change a node's kind, title, body, priority, or kind-defined fields.

    @purpose  Field *values* stay permissive (check reports schema breaches);
              structure stays strict (reserved keys are not fields, kinds must
              exist).
    @tags     ops, update
    """
    plan = Plan.load(root)
    record = _record(plan, node_id)
    for name in (*(set_fields or {}), *unset_fields):
        if name in RESERVED_KEYS:
            raise KumihimoError(f"'{name}' is not a field; use the dedicated op")
    if kind is not None:
        if kind not in plan.kinds:
            known = ", ".join(sorted(plan.kinds)) or "none defined"
            raise KumihimoError(f"unknown kind '{kind}' (this plan defines: {known})")
        record.fm["kind"] = kind
    if title is not None:
        record.fm["title"] = title
    if priority is not None:
        if priority:
            record.fm["priority"] = priority
        else:
            record.fm.pop("priority", None)
    for name, value in (set_fields or {}).items():
        record.fm[name] = value
    for name in unset_fields:
        if name not in record.fm:
            raise KumihimoError(f"'{node_id}' has no field '{name}'")
        del record.fm[name]
    if body is not None:
        record.body = body
    return _save_and_reload(root, record).node(node_id)


def link(
    root: Path,
    src: str,
    *,
    needs: str | None = None,
    in_: str | None = None,
    to: str | None = None,
    rel: str = "see-also",
) -> Node:
    """Draw one edge from src: a dependency, a membership, or an annotation.

    @purpose  Exactly one edge per call; needs-edges are refused (with the path)
              when they would close a cycle, so no tool can write one.
    @tags     ops, link, cycle-guard
    """
    chosen = [value for value in (needs, in_, to) if value is not None]
    if len(chosen) != 1:
        raise KumihimoError("give exactly one of needs=, in_=, or to=")
    plan = Plan.load(root)
    record = _record(plan, src)
    target = chosen[0]
    _require_exists(plan, target, "edge")
    if needs is not None:
        if target == src:
            raise KumihimoError(f"'{src}' cannot need itself")
        if target in record.node.needs:
            raise KumihimoError(f"'{src}' already needs '{target}'")
        candidate = record.node.model_copy(update={"needs": [*record.node.needs, target]})
        cycle = graph.find_cycle({**plan.nodes, src: candidate})
        if cycle:
            rendered = " -> ".join([*cycle, cycle[0]])
            raise KumihimoError(f"refused: that edge closes a cycle ({rendered})")
        _list_add(record, "needs", target)
    elif in_ is not None:
        if target in record.node.in_:
            raise KumihimoError(f"'{src}' is already in '{target}'")
        _list_add(record, "in", target)
    else:
        entries = record.fm.get("links")
        if not isinstance(entries, list):
            entries = CommentedSeq()
            record.fm["links"] = entries
        if rel == "see-also":
            entries.append(target)
        else:
            entries.append({"to": target, "rel": rel})
    return _save_and_reload(root, record).node(src)


def unlink(
    root: Path,
    src: str,
    *,
    needs: str | None = None,
    in_: str | None = None,
    to: str | None = None,
) -> Node:
    """Remove one edge from src.

    @purpose  The inverse of link; removing an absent edge is an error, not a
              shrug, so tools notice their own stale state.
    @tags     ops, unlink
    """
    chosen = [value for value in (needs, in_, to) if value is not None]
    if len(chosen) != 1:
        raise KumihimoError("give exactly one of needs=, in_=, or to=")
    plan = Plan.load(root)
    record = _record(plan, src)
    if needs is not None:
        _list_remove(record, "needs", needs)
    elif in_ is not None:
        _list_remove(record, "in", in_)
    else:
        entries = record.fm.get("links")
        found = None
        if isinstance(entries, list):
            for item in entries:
                if item == to or (isinstance(item, dict) and item.get("to") == to):
                    found = item
                    break
        if found is None or not isinstance(entries, list):
            raise KumihimoError(f"'{src}' has no links entry '{to}'")
        entries.remove(found)
        if len(entries) == 0:
            del record.fm["links"]
    return _save_and_reload(root, record).node(src)


def _rewrite_reference(record: NodeRecord, old: str, new: str) -> bool:
    """Replace old with new anywhere this record references it.

    @purpose  Rename's referrer fixup: needs, in, and links entries, whatever
              their spelling (scalar, list item, or {to, rel} mapping).
    """
    changed = False
    for key in ("needs", "in"):
        value = record.fm.get(key)
        if isinstance(value, str) and value == old:
            record.fm[key] = new
            changed = True
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if item == old:
                    value[index] = new
                    changed = True
    entries = record.fm.get("links")
    if isinstance(entries, list):
        for index, item in enumerate(entries):
            if item == old:
                entries[index] = new
                changed = True
            elif isinstance(item, dict) and item.get("to") == old:
                item["to"] = new
                changed = True
    return changed


def rename_node(root: Path, old: str, new: str) -> Node:
    """Move a node to a new id, fixing every referrer and the view layout.

    @purpose  Renames are safe or they don't happen: the renamed file's bytes
              never change (the id is the filename), and no reference is left
              pointing at the old name.
    @tags     ops, rename, referrer-fixup
    """
    plan = Plan.load(root)
    _record(plan, old)
    _require_slug(new)
    if old == new:
        raise KumihimoError("old and new ids are the same")
    lowered = {existing.lower() for existing in plan.records if existing != old}
    if new.lower() in lowered:
        raise KumihimoError(f"node '{new}' already exists")
    old_path = plan.records[old].path
    new_path = plan.root / store.NODES_DIR / Path(new + ".md")
    new_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.rename(new_path)
    changed = [
        record
        for node_id, record in plan.records.items()
        if node_id != old and _rewrite_reference(record, old, new)
    ]
    _save_and_reload(root, *changed)
    view = store.load_view(plan.root)
    if view is not None:
        layout = view.get("layout")
        if isinstance(layout, dict) and old in layout:
            layout[new] = layout.pop(old)
            store.save_view(plan.root, view)
    return Plan.load(root).node(new)


def remove_node(root: Path, node_id: str, *, force: bool = False) -> list[str]:
    """Delete a node; with force, strip every reference to it first.

    @purpose  A referenced node refuses to die quietly — the error names the
              referrers, and force removes the edges in the same operation so
              the plan is never left dangling.
    @tags     ops, remove
    """
    plan = Plan.load(root)
    record = _record(plan, node_id)
    referrers = [
        other.id
        for other in plan.nodes.values()
        if other.id != node_id
        and (
            node_id in other.needs
            or node_id in other.in_
            or any(link_.to == node_id for link_ in other.links)
        )
    ]
    if referrers and not force:
        names = ", ".join(sorted(referrers))
        raise KumihimoError(f"'{node_id}' is referenced by: {names} (use force to strip)")
    changed: list[NodeRecord] = []
    for referrer in referrers:
        other = plan.records[referrer]
        for key in ("needs", "in"):
            value = other.fm.get(key)
            if isinstance(value, str) and value == node_id:
                del other.fm[key]
            elif isinstance(value, list) and node_id in value:
                value.remove(node_id)
                if len(value) == 0:
                    del other.fm[key]
        entries = other.fm.get("links")
        if isinstance(entries, list):
            keep = [
                item
                for item in entries
                if not (item == node_id or (isinstance(item, dict) and item.get("to") == node_id))
            ]
            if len(keep) != len(entries):
                if keep:
                    entries.clear()
                    entries.extend(keep)
                else:
                    del other.fm["links"]
        changed.append(other)
    if changed:
        _save_and_reload(root, *changed)
    record.path.unlink()
    view = store.load_view(plan.root)
    if view is not None:
        layout = view.get("layout")
        if isinstance(layout, dict) and node_id in layout:
            del layout[node_id]
            store.save_view(plan.root, view)
    return sorted(referrers)
