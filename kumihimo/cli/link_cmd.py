"""
@file        kumihimo/cli/link_cmd.py
@purpose     `kumihimo link` — draw one edge: --needs for dependency, --in for
             membership, --to/--rel for annotation. Cycle refusals surface with
             their path.
@layer       cli
@tags        cli, link, edges
@related     kumihimo/core/ops.py (link does the work and guards cycles)
@design      PLAN.md §1, §3.1
"""

from __future__ import annotations

from pathlib import Path

import typer

from kumihimo.cli.common import console, die
from kumihimo.core import ops
from kumihimo.core.errors import KumihimoError


def link(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    src: str = typer.Argument(..., metavar="SRC", help="Source node id."),
    needs: str | None = typer.Option(None, "--needs", help="SRC depends on this id."),
    in_: str | None = typer.Option(None, "--in", help="SRC belongs to this id."),
    to: str | None = typer.Option(None, "--to", help="Annotation target id."),
    rel: str = typer.Option("see-also", "--rel", help="Annotation relation label."),
) -> None:
    """Draw one edge between two nodes.

    @purpose  The graph from the shell: dependency, membership, or annotation —
              exactly one per call, refused with the path if it would cycle.
    """
    try:
        node = ops.link(plan_path, src, needs=needs, in_=in_, to=to, rel=rel, actor="cli")
    except KumihimoError as err:
        die(str(err))
    if needs is not None:
        console.print(f"[bold]{node.id}[/bold] now needs [bold]{needs}[/bold]")
    elif in_ is not None:
        console.print(f"[bold]{node.id}[/bold] is now in [bold]{in_}[/bold]")
    else:
        console.print(f"[bold]{node.id}[/bold] now links to [bold]{to}[/bold] ({rel})")
