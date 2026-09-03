"""
@file        kumihimo/cli/add_cmd.py
@purpose     `kumihimo add` — create a node from flags, coercing --field values
             through the kind's field specs (ints, bools, comma-lists) so typed
             fields are reachable from a shell.
@layer       cli
@tags        cli, add, field-coercion
@related     kumihimo/core/ops.py (add_node does the work),
             kumihimo/core/kinds.py (field specs drive coercion)
@design      PLAN.md §1
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from kumihimo.cli.common import console, die
from kumihimo.core import ops
from kumihimo.core.errors import KumihimoError
from kumihimo.core.model import FieldSpec
from kumihimo.core.plan import Plan


def _coerce(spec: FieldSpec | None, raw: str) -> Any:
    """Turn a --field string into the type its spec expects.

    @purpose  `--field priority-ish=3` and `--field acceptance=a,b` mean the int
              and the list, not their spellings; unknown fields stay strings and
              validation warns.
    """
    if spec is None or spec.type in ("str", "choice"):
        return raw
    if spec.type == "int":
        try:
            return int(raw)
        except ValueError:
            return raw
    if spec.type == "bool":
        if raw.lower() in ("true", "yes", "1"):
            return True
        if raw.lower() in ("false", "no", "0"):
            return False
        return raw
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_fields(plan: Plan, kind: str, pairs: list[str]) -> dict[str, Any]:
    """Split key=value flags and coerce each through the kind's specs.

    @purpose  One malformed pair should name itself, not half-apply.
    """
    specs = plan.kinds[kind].fields if kind in plan.kinds else {}
    fields: dict[str, Any] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            die(f"--field wants key=value, got '{pair}'")
        fields[key] = _coerce(specs.get(key), value)
    return fields


def add(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    node_id: str = typer.Argument(..., metavar="ID", help="New node id (slug)."),
    kind: str = typer.Option("task", "--kind", help="Node kind."),
    title: str | None = typer.Option(None, "--title"),
    body: str = typer.Option("", "--body", help="Node body text."),
    needs: list[str] = typer.Option([], "--needs", help="Dependency id (repeatable, or a,b)."),
    in_: list[str] = typer.Option([], "--in", help="Membership target id (repeatable)."),
    field: list[str] = typer.Option([], "--field", help="key=value (repeatable)."),
) -> None:
    """Add a node to a plan.

    @purpose  Flag-driven node creation — no editor spawning, so it scripts and
              it works from anything that can run a command.
    """
    try:
        plan = Plan.load(plan_path)
        fields = parse_fields(plan, kind, field)
        split_needs = tuple(n for item in needs for n in item.split(",") if n)
        split_in = tuple(g for item in in_ for g in item.split(",") if g)
        node = ops.add_node(
            plan.root,
            node_id,
            kind,
            title=title,
            body=body,
            fields=fields,
            needs=split_needs,
            in_=split_in,
            actor="cli",
        )
    except KumihimoError as err:
        die(str(err))
    console.print(f"added [bold]{node.id}[/bold] ({node.kind})")
