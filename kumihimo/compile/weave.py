"""
@file        kumihimo/compile/weave.py
@purpose     Stage four of the braid: assign global numbers across the strategy's
             sections, render every intro and item, and wrap the whole in the
             cord template (built-in, or the plan's own via compile.cord) with
             the Mermaid overview, stub acknowledgements, the Cast section
             (crew nodes the strategy carved out), and the --for grounding line.
@layer       compile
@tags        braid, weave, cord, numbering, cast, ground-with
@related     kumihimo/compile/templates/cord.j2 (the built-in cord),
             kumihimo/compile/render.py (renders what this numbers, and
             builds each Cast entry)
@design      PLAN.md §4.1 step 4, PLAN2.md §3.3
"""

from __future__ import annotations

import re
from importlib import resources
from typing import TYPE_CHECKING

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from kumihimo.compile import diagram as diagram_module
from kumihimo.compile.render import Renderer, build_context, cast_entry
from kumihimo.core.errors import KumihimoError

if TYPE_CHECKING:
    from kumihimo.compile.select import Selection
    from kumihimo.compile.strategies import Section
    from kumihimo.core.plan import Plan

_EXCESS_BLANKS = re.compile(r"\n{3,}")


def _cord_source(plan: Plan) -> str:
    """The cord template text: the plan's own file, or the built-in.

    @purpose  compile.cord in the manifest points at a file under the plan root;
              absent, every plan shares the same proven cord.
    """
    custom = plan.manifest.compile.cord
    if custom:
        path = plan.root / custom
        if not path.is_file():
            raise KumihimoError(f"compile.cord: template file '{custom}' not found")
        return path.read_text(encoding="utf-8")
    builtin = resources.files("kumihimo") / "compile" / "templates" / "cord.j2"
    return builtin.read_text(encoding="utf-8")


def assign_numbers(sections: list[Section]) -> dict[str, int]:
    """Global 1..N numbering over every section member, in reading order.

    @purpose  After-references stay unambiguous across sections because numbering
              never restarts.
    """
    numbers: dict[str, int] = {}
    counter = 0
    for section in sections:
        for node_id in section.node_ids:
            counter += 1
            numbers[node_id] = counter
    return numbers


def weave(
    plan: Plan,
    sections: list[Section],
    selection: Selection,
    *,
    diagram: bool,
    warnings: list[str],
    cast_ids: list[str] | None = None,
    ground_with: str | None = None,
) -> str:
    """Render everything and assemble the cord.

    @purpose  The braid's final text: deterministic to the byte, tidy regardless
              of template whitespace, always ending in exactly one newline.
              cast_ids (every crew member the rendered items cite, whether or
              not that member is itself selected — braid.py's _cast_ids owns
              the rule) and ground_with (a --for agent's retrieval field) are
              additive: both default to nothing, so a plan with no crew
              renders exactly as before K29.
    @tags     weave, cord, cast, ground-with
    """
    renderer = Renderer(plan)
    numbers = assign_numbers(sections)
    previous: str | None = None
    woven_sections: list[dict[str, object]] = []
    for section in sections:
        intro = None
        if section.intro_id is not None:
            context = build_context(
                plan,
                section.intro_id,
                numbers=numbers,
                selection=selection,
                group_id=None,
                previous_id=None,
            )
            intro = renderer.render(section.intro_id, context)
        items: list[str] = []
        for node_id in section.node_ids:
            context = build_context(
                plan,
                node_id,
                numbers=numbers,
                selection=selection,
                group_id=section.intro_id,
                previous_id=previous,
            )
            items.append(renderer.render(node_id, context))
            previous = node_id
        # Key name "entries", not "items": Jinja resolves dict.items (the method)
        # before the key, and the cord template iterates section.entries.
        woven_sections.append({"title": section.title, "intro": intro, "entries": items})

    mermaid_text = diagram_module.mermaid(plan, selection) if diagram else ""
    stub_titles = ", ".join(plan.nodes[stub].title for stub in selection.stubs)
    cast = [cast_entry(plan, node_id) for node_id in (cast_ids or [])]
    env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    try:
        cord = env.from_string(_cord_source(plan))
        text = cord.render(
            plan={"name": plan.manifest.plan, "description": plan.manifest.description},
            preamble=plan.manifest.compile.preamble.strip(),
            epilogue=plan.manifest.compile.epilogue.strip(),
            diagram=mermaid_text,
            stubs=stub_titles,
            cast=cast,
            ground_with=ground_with,
            sections=woven_sections,
            warnings=warnings,
        )
    except TemplateError as err:
        raise KumihimoError(f"cord template failed: {err}") from err
    return _EXCESS_BLANKS.sub("\n\n", text).strip("\n") + "\n"
