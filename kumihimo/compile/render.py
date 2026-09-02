"""
@file        kumihimo/compile/render.py
@purpose     Stage three of the braid: each node through its kind's Jinja2
             template, sandboxed. Resolves templates (manifest inline or file →
             pack file → built-in default), builds the per-node context (deps
             with numbers, group, stub markers, independence notes, mentions,
             consult-links), turns template errors into errors that name the
             kind, and builds Cast-section entries for agent/skill nodes.
@layer       compile
@tags        braid, render, jinja, templates, context, mentions, cast
@related     kumihimo/packs/engineering/templates (the pack's kind templates),
             kumihimo/compile/weave.py (assigns the numbers this renders,
             calls cast_entry for the Cast section)
@design      PLAN.md §4.1 step 3, PLAN2.md §3.3
"""

from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING, Any

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from kumihimo.core import graph, kinds
from kumihimo.core.errors import KumihimoError

if TYPE_CHECKING:
    from kumihimo.compile.select import Selection
    from kumihimo.core.model import Node
    from kumihimo.core.plan import Plan

# Written for a trim_blocks environment: newlines ride inside expression output
# (immune to trimming), and the one deliberately doubled newline below survives
# as the blank line before the body.
DEFAULT_TEMPLATE = (
    "{% if number %}### {{ number }}. {{ node.title }} ({{ node.kind }})\n"
    "{% else %}{{ node.title }} ({{ node.kind }})\n"
    "{% endif %}"
    "{% if after %}*After:* {{ after }}\n{% endif %}"
    "{% if independent %}*Independent of the item above.*\n{% endif %}"
    "{% for name, value in node.fields.items() %}"
    "{{ name }}: "
    "{% if value is iterable and value is not string %}"
    '{{ value | join("; ") }}\n'
    "{% else %}"
    "{{ value }}\n"
    "{% endif %}"
    "{% endfor %}\n\n{{ node.body }}\n"
)


class Renderer:
    """Compiled templates and context building for one plan.

    @purpose  One sandboxed environment, one template per kind, resolved once —
              rendering N nodes must not re-read N files.
    @tags     render, templates
    """

    def __init__(self, plan: Plan) -> None:
        """Compile every selected kind's template up front.

        @purpose  Template errors surface before any output exists, naming the
                  kind, not half-way through a document.
        """
        self._plan = plan
        self._env = SandboxedEnvironment(
            trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True
        )
        self._templates: dict[str, Any] = {}

    def _template_source(self, kind_name: str) -> str:
        """Where a kind's template text comes from, in precedence order.

        @purpose  Manifest inline or file wins; then the pack's templates/<kind>.j2;
                  then the built-in generic — every kind always renders somehow.
        """
        kind = self._plan.kinds.get(kind_name)
        if kind and kind.template:
            if "{{" in kind.template or "{%" in kind.template or "\n" in kind.template:
                return kind.template
            path = self._plan.root / kind.template
            if not path.is_file():
                raise KumihimoError(
                    f"kind '{kind_name}': template file '{kind.template}' not found"
                )
            return path.read_text(encoding="utf-8")
        pack = self._plan.manifest.pack
        if pack:
            candidate = resources.files("kumihimo") / "packs" / pack / "templates"
            candidate = candidate / f"{kind_name}.j2"
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        return DEFAULT_TEMPLATE

    def render(self, node_id: str, context: dict[str, Any]) -> str:
        """One node through its kind's template.

        @purpose  The only call site for Jinja: errors become 'template for kind X'.
        """
        node = self._plan.nodes[node_id]
        key = node.kind or "?"
        if key not in self._templates:
            try:
                self._templates[key] = self._env.from_string(self._template_source(key))
            except TemplateError as err:
                raise KumihimoError(f"template for kind '{key}' does not parse: {err}") from err
        try:
            return str(self._templates[key].render(**context))
        except TemplateError as err:
            raise KumihimoError(f"template for kind '{key}' failed on '{node_id}': {err}") from err


def _reference(plan: Plan, dep: str, numbers: dict[str, int], stubs: set[str]) -> str:
    """How one dependency is spoken of in an After line.

    @purpose  Numbered items by number and title; stubs marked already-in-place;
              unnumbered intros by title alone. The prompt never says just 'see
              above'.
    """
    title = plan.nodes[dep].title
    if dep in numbers:
        return f"{numbers[dep]}. {title}"
    if dep in stubs:
        return f"{title} (already in place)"
    return title


def _mentions(plan: Plan, ids: list[str]) -> str:
    """A mention list (agents:/skills:/trains: targets) as 'Title (id)' pairs.

    @purpose  Unlike a `needs` dependency, a mentioned agent or skill is not
              guaranteed a number in this document — Cast pulls crew nodes out
              of the numbered flow, and a --for slice may not select the
              mentioned node at all. The id is the one handle that stays
              correct regardless, so mentions cite by title *and* id (house
              style judgment call, documented at K29 — see task.j2).
    @tags     mentions, rendering
    """
    return ", ".join(
        f"{plan.nodes[target].title} ({target})" for target in ids if target in plan.nodes
    )


def _split_links(plan: Plan, node: Node) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Partition a node's links into consult-links (rel=consult, target kind
    reference) and everything else.

    @purpose  PLAN2 §3.7: a consult-link renders as its own *Consult:* line
              with the reference's locator/retriever, not folded into the
              generic See-also list; a rel=consult link to a non-reference
              target is not a consult-link and renders exactly as before.
    @tags     mentions, consult, links
    """
    consults: list[dict[str, str]] = []
    others: list[dict[str, str]] = []
    for link in node.links:
        target = plan.nodes.get(link.to)
        if target is None:
            continue
        if link.rel == "consult" and target.kind == "reference":
            kind = plan.kinds.get(target.kind)
            effective = kinds.effective_fields(target, kind) if kind else dict(target.fields)
            retriever = str(effective.get("retriever") or "")
            consults.append(
                {
                    "title": target.title,
                    "locator": str(effective.get("locator") or ""),
                    "retriever": retriever,
                    # Pre-joined for the same reason cast_entry's detail_text
                    # is: a trailing {% endif %} on this line would eat the
                    # blank line before the body under trim_blocks.
                    "via_text": f" (via {retriever})" if retriever else "",
                }
            )
        else:
            others.append({"to": link.to, "rel": link.rel, "title": target.title})
    return consults, others


def build_context(
    plan: Plan,
    node_id: str,
    *,
    numbers: dict[str, int],
    selection: Selection,
    group_id: str | None,
    previous_id: str | None,
) -> dict[str, Any]:
    """Everything a kind template may look at, for one node.

    @purpose  The template contract, in one place: node (effective fields), the
              composed After line, deps/dependents with numbers, group, and the
              independence note.
    @tags     context, templates
    """
    node: Node = plan.nodes[node_id]
    kind = plan.kinds.get(node.kind)
    effective = kinds.effective_fields(node, kind) if kind else dict(node.fields)
    stubs = set(selection.stubs)
    selected = set(selection.ids)
    deps = [dep for dep in node.needs if dep in plan.nodes]
    dependents = sorted(
        other.id for other in plan.nodes.values() if node_id in other.needs and other.id in selected
    )
    independent = False
    if previous_id is not None and numbers.get(node_id):
        independent = previous_id not in graph.ancestors(plan.nodes, node_id)
    in_others = [
        plan.nodes[target].title
        for target in node.in_
        if target in plan.nodes and target != group_id
    ]
    consults, other_links = _split_links(plan, node)
    return {
        "plan": {"name": plan.manifest.plan, "description": plan.manifest.description},
        "node": {
            "id": node.id,
            "kind": node.kind,
            "title": node.title,
            "body": node.body.strip("\n"),
            "fields": effective,
            "priority": node.priority,
        },
        "number": numbers.get(node_id),
        "after": "; ".join(_reference(plan, dep, numbers, stubs) for dep in deps),
        "deps": [
            {"id": dep, "title": plan.nodes[dep].title, "number": numbers.get(dep)} for dep in deps
        ],
        "dependents": [
            {"id": other, "title": plan.nodes[other].title, "number": numbers.get(other)}
            for other in dependents
        ],
        "group": (
            {"id": group_id, "title": plan.nodes[group_id].title} if group_id is not None else None
        ),
        "in_others": in_others,
        "links": other_links,
        "consults": consults,
        "assigned": _mentions(plan, node.agents),
        "with_skills": _mentions(plan, node.skills),
        "trains": _mentions(plan, node.trains),
        "independent": independent,
    }


def cast_entry(plan: Plan, node_id: str) -> dict[str, Any]:
    """One Cast-section row: title, kind, and its informative fields in order.

    @purpose  Grouped's Cast section briefs the crew before the work (PLAN2
              §3.3): agent shows runtime/model/entry, skill shows invocation/
              source/cadence, both end with trained — present fields only, no
              empty placeholders, and never through the node's own kind
              template (that would give it a numbered card among the work).
    @tags     cast, mentions, rendering
    """
    node = plan.nodes[node_id]
    kind = plan.kinds.get(node.kind)
    effective = kinds.effective_fields(node, kind) if kind else dict(node.fields)
    field_order = {
        "agent": ("runtime", "model", "entry", "trained"),
        "skill": ("invocation", "source", "cadence", "trained"),
    }.get(node.kind, ())
    details = [f"{name}: {effective[name]}" for name in field_order if effective.get(name)]
    # Pre-joined so cord.j2's Cast loop is one expression per row: a literal
    # newline after a trailing {% endif %} would vanish under trim_blocks
    # (the same gotcha DEFAULT_TEMPLATE's own comment documents).
    detail_text = f" — {' · '.join(details)}" if details else ""
    return {
        "id": node.id,
        "title": node.title,
        "kind": node.kind,
        "details": details,
        "detail_text": detail_text,
    }
