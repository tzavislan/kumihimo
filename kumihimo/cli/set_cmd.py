"""
@file        kumihimo/cli/set_cmd.py
@purpose     `kumihimo set` — update a node from the shell: title, kind, body,
             priority, fields (coerced through the kind's specs), and unsets.
             The verb dogfooding found missing when the roadmap needed titles.
@layer       cli
@tags        cli, set, update, field-coercion
@related     kumihimo/core/ops.py (update_node does the work),
             kumihimo/cli/add_cmd.py (shares the field coercion)
@design      PLAN.md §1, queue item K16
"""

from __future__ import annotations

from pathlib import Path

import typer

from kumihimo.cli.add_cmd import parse_fields
from kumihimo.cli.common import console, die
from kumihimo.core import ops
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan


def set_cmd(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    node_id: str = typer.Argument(..., metavar="ID", help="Node to update."),
    title: str | None = typer.Option(None, "--title"),
    kind: str | None = typer.Option(None, "--kind"),
    body: str | None = typer.Option(None, "--body"),
    priority: int | None = typer.Option(None, "--priority"),
    field: list[str] = typer.Option([], "--field", help="key=value (repeatable)."),
    unset: list[str] = typer.Option([], "--unset", help="Field name to remove (repeatable)."),
) -> None:
    """Update a node's title, kind, body, priority, or fields.

    @purpose  ops.update_node from the shell, with the same --field coercion as
              add — the gap the roadmap dogfood found.
    """
    try:
        plan = Plan.load(plan_path)
        target_kind = kind or plan.node(node_id).kind
        fields = parse_fields(plan, target_kind, field)
        node = ops.update_node(
            plan.root,
            node_id,
            kind=kind,
            title=title,
            body=body,
            priority=priority,
            set_fields=fields or None,
            unset_fields=tuple(unset),
        )
    except KumihimoError as err:
        die(str(err))
    console.print(f"updated [bold]{node.id}[/bold]")
