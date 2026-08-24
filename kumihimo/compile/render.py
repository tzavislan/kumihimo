"""
@file        kumihimo/compile/render.py
@purpose     Stage three of the braid: each node through its kind's Jinja2
             template, sandboxed. Resolves templates (manifest inline or file →
             pack file → built-in default), builds the per-node context (deps
             with numbers, group, stub markers, independence notes), and turns
             template errors into errors that name the kind.
@layer       compile
@tags        braid, render, jinja, templates, context
@related     kumihimo/packs/engineering/templates (the pack's kind templates),
             kumihimo/compile/weave.py (assigns the numbers this renders)
@design      PLAN.md §4.1 step 3
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
        "links": [
            {"to": link.to, "rel": link.rel, "title": plan.nodes[link.to].title}
            for link in node.links
            if link.to in plan.nodes
        ],
        "independent": independent,
    }
