"""
@file        kumihimo/core/store.py
@purpose     The on-disk truth: locates a plan, parses the manifest and node
             files (frontmatter round-tripped through ruamel, body kept as raw
             bytes-in-string), and writes back with the fidelity contract —
             untouched files are never written, touched files keep their
             comments, key order, newline style, and BOM.
@layer       core
@tags        store, frontmatter, round-trip, fidelity, atomic-write
@related     kumihimo/core/plan.py (the facade over this),
             kumihimo/core/ops.py (mutates records then saves through this),
             tests/test_store_roundtrip.py (the contract, executable)
@design      PLAN.md §3.3
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError

from kumihimo.core.errors import KumihimoError
from kumihimo.core.model import (
    SLUG_RE,
    CompileSettings,
    Finding,
    Link,
    Manifest,
    Node,
    default_title,
)

MANIFEST_NAME = "kumihimo.yaml"
NODES_DIR = "nodes"
VIEW_NAME = "view.yaml"
BOM = "\ufeff"


def _yaml() -> YAML:
    """A round-trip YAML instance configured for fidelity.

    @purpose  One place for the knobs that keep user formatting intact: preserve
              quotes, never re-wrap long lines.
    """
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 100000
    # Canonical block style: two spaces then "- ". Untouched files never re-serialize,
    # so this only shapes new frontmatter and normalizes files an op actually edited.
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


@dataclass
class NodeRecord:
    """One node file: the parsed Node plus everything needed to write it back
    exactly.

    @purpose  The unit of the fidelity contract — the live frontmatter map (edits
              go here so comments survive), the raw body, the file's own newline
              style and BOM, and the dirty flag that gates every write.
    """

    node: Node
    fm: CommentedMap
    body: str
    newline: str
    bom: bool
    path: Path
    original: str
    dirty: bool = False


@dataclass
class LoadedPlan:
    """Everything read from a plan directory in one pass.

    @purpose  The store's whole answer to "load this": manifest with its raw map,
              node records, and every finding produced along the way.
    """

    root: Path
    manifest: Manifest
    manifest_raw: CommentedMap
    records: dict[str, NodeRecord]
    findings: list[Finding] = field(default_factory=list)


def find_root(path: Path) -> Path:
    """Resolve a user-supplied path to a plan root.

    @purpose  Every entry point accepts "the plan directory" and fails with the
              same sentence when it isn't one.
    """
    root = path.resolve()
    if not (root / MANIFEST_NAME).is_file():
        raise KumihimoError(f"not a kumihimo plan: no {MANIFEST_NAME} in {root}")
    return root


def _read_text(path: Path) -> tuple[str, str, bool]:
    """Read a file preserving its newline style and BOM as facts.

    @purpose  Text with "\\r\\n" left intact in the string is what makes writing it
              back byte-identical possible.
    """
    raw = path.read_bytes().decode("utf-8")
    bom = raw.startswith(BOM)
    if bom:
        raw = raw[len(BOM) :]
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw, newline, bom


def split_frontmatter(text: str) -> tuple[str, str] | None:
    """Split a node file into (frontmatter text, raw body).

    @purpose  The body is everything after the closing delimiter line, verbatim —
              the store never reflows prose. None means no well-formed block.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :])
    return None


def _as_str_list(value: Any) -> list[str] | None:
    """Coerce a frontmatter scalar-or-list into a list of strings.

    @purpose  `needs: api` and `needs: [api]` both mean one edge; anything that
              isn't strings means the file is wrong, not half-right.
    """
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _parse_links(value: Any, node_id: str, findings: list[Finding]) -> list[Link]:
    """Parse the links list: strings or {to, rel} mappings.

    @purpose  Annotation edges stay cheap to write (`links: [redis-outage]`) while
              still carrying a relation label when the author wants one.
    """
    if not isinstance(value, list):
        findings.append(Finding(level="error", where=node_id, message="'links' must be a list"))
        return []
    links: list[Link] = []
    for item in value:
        if isinstance(item, str):
            links.append(Link(to=item))
        elif isinstance(item, dict) and isinstance(item.get("to"), str):
            links.append(Link(to=item["to"], rel=str(item.get("rel", "see-also"))))
        else:
            message = f"link entry {item!r} needs a 'to' (and optional 'rel')"
            findings.append(Finding(level="error", where=node_id, message=message))
    return links


def _node_from_fm(node_id: str, fm: CommentedMap, body: str, findings: list[Finding]) -> Node:
    """Build a Node from a parsed frontmatter map, normalizing tolerantly.

    @purpose  User files produce precise findings, never exceptions; whatever can
              be salvaged loads so the rest of the plan stays usable.
    @tags     frontmatter, normalization, findings
    """
    data: dict[str, Any] = dict(fm)
    kind = data.pop("kind", "")
    if not isinstance(kind, str):
        findings.append(Finding(level="error", where=node_id, message="'kind' must be text"))
        kind = ""
    title = data.pop("title", "")
    if not isinstance(title, str):
        findings.append(Finding(level="error", where=node_id, message="'title' must be text"))
        title = ""
    edges: dict[str, list[str]] = {}
    for key in ("needs", "in"):
        raw = data.pop(key, [])
        listed = _as_str_list(raw) if raw != [] else []
        if listed is None:
            message = f"'{key}' must be an id or list of ids"
            findings.append(Finding(level="error", where=node_id, message=message))
            listed = []
        edges[key] = listed
    raw_links = data.pop("links", None)
    links = _parse_links(raw_links, node_id, findings) if raw_links is not None else []
    priority = data.pop("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int):
        findings.append(
            Finding(level="error", where=node_id, message="'priority' must be an integer")
        )
        priority = 0
    return Node(
        id=node_id,
        kind=kind,
        title=title or default_title(node_id),
        needs=edges["needs"],
        in_=edges["in"],
        links=links,
        priority=priority,
        fields=data,
        body=body,
    )


def _load_record(path: Path, root: Path, findings: list[Finding]) -> NodeRecord:
    """Load one node file into a record, reporting problems as findings.

    @purpose  A malformed file still yields a record (empty frontmatter, body
              preserved) so a typo can't hide a node from the graph entirely.
    """
    node_id = path.relative_to(root / NODES_DIR).with_suffix("").as_posix()
    text, newline, bom = _read_text(path)
    where = node_id
    if not SLUG_RE.match(node_id):
        message = "id (from filename) must be lowercase [a-z0-9-], with / for namespaces"
        findings.append(Finding(level="error", where=where, message=message))
    parts = split_frontmatter(text)
    fm: CommentedMap = CommentedMap()
    body = text
    if parts is None:
        message = "missing or unterminated frontmatter block (--- ... --- at the top of the file)"
        findings.append(Finding(level="error", where=where, message=message))
    else:
        fm_text, body = parts
        try:
            # Parse with LF only: ruamel would otherwise capture \r inside comment
            # tokens and emit \r\r\n when the record's newline style is applied.
            loaded = _yaml().load(fm_text.replace("\r\n", "\n"))
        except YAMLError as err:
            mark = getattr(err, "problem_mark", None)
            at = f" (frontmatter line {mark.line + 1})" if mark else ""
            findings.append(
                Finding(level="error", where=where, message=f"frontmatter is not valid YAML{at}")
            )
            loaded = None
        if loaded is None:
            fm = CommentedMap()
        elif isinstance(loaded, CommentedMap):
            fm = loaded
        else:
            message = "frontmatter must be a mapping of keys to values"
            findings.append(Finding(level="error", where=where, message=message))
    node = _node_from_fm(node_id, fm, body, findings)
    return NodeRecord(
        node=node, fm=fm, body=body, newline=newline, bom=bom, path=path, original=text
    )


def case_collisions(ids: list[str]) -> list[str]:
    """Ids that collide when lowercased.

    @purpose  A plan authored on Linux must clone onto Windows/macOS; two files
              differing only in case cannot.
    """
    seen: dict[str, str] = {}
    collided: list[str] = []
    for node_id in sorted(ids):
        low = node_id.lower()
        if low in seen and seen[low] != node_id:
            collided.append(node_id)
        seen.setdefault(low, node_id)
    return collided


def load_manifest(root: Path) -> tuple[Manifest, CommentedMap, list[Finding]]:
    """Parse kumihimo.yaml into a Manifest plus its raw round-trip map.

    @purpose  Manifest problems are findings against 'kumihimo.yaml'; a broken
              manifest still returns defaults so nodes can load and be checked.
    """
    findings: list[Finding] = []
    where = MANIFEST_NAME
    text, _, _ = _read_text(root / MANIFEST_NAME)
    try:
        loaded = _yaml().load(text)
    except YAMLError:
        findings.append(Finding(level="error", where=where, message="manifest is not valid YAML"))
        loaded = None
    raw = loaded if isinstance(loaded, CommentedMap) else CommentedMap()
    if loaded is not None and not isinstance(loaded, CommentedMap):
        findings.append(Finding(level="error", where=where, message="manifest must be a mapping"))
    fmt = raw.get("format", 1)
    if fmt != 1:
        message = f"unsupported format {fmt!r}; this kumihimo understands format 1"
        findings.append(Finding(level="error", where=where, message=message))
    kinds_raw = raw.get("kinds") or {}
    pack: str | None = None
    overrides: dict[str, Any] = {}
    if isinstance(kinds_raw, dict):
        pack_value = kinds_raw.get("from")
        if pack_value is not None and not isinstance(pack_value, str):
            findings.append(
                Finding(level="error", where=where, message="kinds.from must be a pack name")
            )
        else:
            pack = pack_value
        overrides = {k: v for k, v in kinds_raw.items() if k != "from"}
    else:
        findings.append(Finding(level="error", where=where, message="'kinds' must be a mapping"))
    try:
        compile_settings = CompileSettings.model_validate(raw.get("compile") or {})
    except ValidationError as err:
        message = f"'compile' settings are invalid: {err.error_count()} problem(s)"
        findings.append(Finding(level="error", where=where, message=message))
        compile_settings = CompileSettings()
    manifest = Manifest(
        format=1,
        plan=str(raw.get("plan", "") or ""),
        description=str(raw.get("description", "") or ""),
        pack=pack,
        kind_overrides=overrides,
        compile=compile_settings,
    )
    return manifest, raw, findings


def load(path: Path) -> LoadedPlan:
    """Load a whole plan directory: manifest, every node, all load findings.

    @purpose  The single read path every client shares; content problems are
              findings, only "not a plan at all" raises.
    """
    root = find_root(path)
    manifest, raw, findings = load_manifest(root)
    records: dict[str, NodeRecord] = {}
    nodes_dir = root / NODES_DIR
    if nodes_dir.is_dir():
        for file in sorted(nodes_dir.rglob("*.md")):
            record = _load_record(file, root, findings)
            records[record.node.id] = record
    for collided in case_collisions(list(records)):
        message = f"id '{collided}' collides with another id when lowercased"
        findings.append(Finding(level="error", where=collided, message=message))
    return LoadedPlan(
        root=root, manifest=manifest, manifest_raw=raw, records=records, findings=findings
    )


def _atomic_write(path: Path, data: bytes) -> None:
    """Write bytes via a sibling temp file and atomic replace.

    @purpose  A crash mid-write must never leave a half-node on disk.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def render_record(record: NodeRecord) -> str:
    """Compose a record back into file text, honoring its newline style.

    @purpose  Only the frontmatter is re-serialized (through the same round-trip
              map, so comments and order survive); the body is appended verbatim.
    """
    if len(record.fm) == 0:
        fm_text = ""
    else:
        buffer = io.StringIO()
        _yaml().dump(record.fm, buffer)
        fm_text = buffer.getvalue()
    if record.newline != "\n":
        fm_text = fm_text.replace("\n", record.newline)
    delimiter = "---" + record.newline
    prefix = BOM if record.bom else ""
    return prefix + delimiter + fm_text + delimiter + record.body


def save_record(record: NodeRecord) -> bool:
    """Write one record if and only if it is dirty; report whether it wrote.

    @purpose  The dirty flag *is* the fidelity guarantee for untouched files —
              no write path exists that rewrites a file nobody edited.
    """
    if not record.dirty:
        return False
    record.path.parent.mkdir(parents=True, exist_ok=True)
    text = render_record(record)
    _atomic_write(record.path, text.encode("utf-8"))
    record.original = text.removeprefix(BOM)
    record.dirty = False
    return True


def save_manifest(root: Path, raw: CommentedMap) -> None:
    """Write the manifest's round-trip map back to kumihimo.yaml.

    @purpose  Manifest edits (rare, op-driven) keep comments the same way node
              frontmatter does.
    """
    buffer = io.StringIO()
    _yaml().dump(raw, buffer)
    _atomic_write(root / MANIFEST_NAME, buffer.getvalue().encode("utf-8"))


def load_view(root: Path) -> CommentedMap | None:
    """Read view.yaml's round-trip map, or None when it doesn't exist.

    @purpose  Layout is a sidecar; ops touch it only for referrer fixup (rename).
    """
    view = root / VIEW_NAME
    if not view.is_file():
        return None
    loaded = _yaml().load(view.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, CommentedMap) else None


def save_view(root: Path, data: CommentedMap) -> None:
    """Write view.yaml back.

    @purpose  Counterpart of load_view for the rare core-side view edit.
    """
    buffer = io.StringIO()
    _yaml().dump(data, buffer)
    _atomic_write(root / VIEW_NAME, buffer.getvalue().encode("utf-8"))


def new_record(root: Path, node: Node) -> NodeRecord:
    """Build a record (and canonical frontmatter) for a node that has no file yet.

    @purpose  New files get the canonical key order — kind, title, needs, in,
              links, priority, then fields — with flow-style edge lists to match
              the documented format.
    """
    fm = CommentedMap()
    fm["kind"] = node.kind
    if node.title and node.title != default_title(node.id):
        fm["title"] = node.title
    for key, values in (("needs", node.needs), ("in", node.in_)):
        if values:
            seq = CommentedSeq(values)
            seq.fa.set_flow_style()
            fm[key] = seq
    if node.links:
        fm["links"] = [{"to": link.to, "rel": link.rel} for link in node.links]
    if node.priority:
        fm["priority"] = node.priority
    for name, value in node.fields.items():
        fm[name] = value
    path = root / NODES_DIR / Path(node.id + ".md")
    return NodeRecord(
        node=node,
        fm=fm,
        body=node.body,
        newline="\n",
        bom=False,
        path=path,
        original="",
        dirty=True,
    )


_STARTER_BODY = (
    "Welcome. This file is one node of your plan; the frontmatter above is the\n"
    "graph. Add more nodes (`kumihimo add`), wire them (`kumihimo link`), keep\n"
    "them honest (`kumihimo check`), and delete this one when it has company.\n"
)


def scaffold(dest: Path, name: str | None = None) -> Path:
    """Create a new plan directory with the engineering pack and a starter node.

    @purpose  `kumihimo new` in library form; refuses to scribble over an
              existing plan.
    """
    root = dest.resolve()
    if (root / MANIFEST_NAME).exists():
        raise KumihimoError(f"{root} is already a kumihimo plan")
    root.mkdir(parents=True, exist_ok=True)
    plan_name = name or root.name
    manifest_text = (
        f"format: 1\nplan: {plan_name}\nkinds:\n  from: engineering\n"
        "compile:\n  strategy: grouped\n"
    )
    _atomic_write(root / MANIFEST_NAME, manifest_text.encode("utf-8"))
    (root / NODES_DIR).mkdir(exist_ok=True)
    starter = Node(id="first-thread", kind="task", title="First thread", body=_STARTER_BODY)
    save_record(new_record(root, starter))
    return root
