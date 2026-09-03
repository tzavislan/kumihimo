"""
@file        kumihimo/cli/link_cmd.py
@purpose     `kumihimo link` — draw one edge: --needs for dependency, --in for
             membership, --to/--rel for annotation, or a crew mention
             (--agents/--skills/--trains, K28/K36-fold-in). Cycle refusals and
             wrong-kind mention targets surface with ops's own wording. There
             is no CLI `unlink` verb (only the MCP/HTTP layers carry one) —
             this file draws edges only, never removes them.
@layer       cli
@tags        cli, link, edges, mentions
@related     kumihimo/core/ops.py (link does the work, guards cycles, and
             checks mention-target kind)
@design      PLAN.md §1, §3.1; PLAN2.md §3.2
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
    agents: str | None = typer.Option(None, "--agents", help="SRC mentions this agent id."),
    skills: str | None = typer.Option(None, "--skills", help="SRC mentions this skill id."),
    trains: str | None = typer.Option(None, "--trains", help="SRC trains this agent or skill id."),
) -> None:
    """Draw one edge between two nodes.

    @purpose  The graph from the shell: dependency, membership, annotation, or
              a crew mention (--agents/--skills/--trains) — exactly one per
              call (ops.link itself enforces that, so the CLI carries no
              second copy of the rule), refused with the path if a needs-edge
              would cycle, or naming the kind it expected if a mention target
              is the wrong kind.
    """
    try:
        node = ops.link(
            plan_path,
            src,
            needs=needs,
            in_=in_,
            to=to,
            rel=rel,
            agents=agents,
            skills=skills,
            trains=trains,
            actor="cli",
        )
    except KumihimoError as err:
        die(str(err))
    if needs is not None:
        console.print(f"[bold]{node.id}[/bold] now needs [bold]{needs}[/bold]")
    elif in_ is not None:
        console.print(f"[bold]{node.id}[/bold] is now in [bold]{in_}[/bold]")
    elif agents is not None:
        console.print(f"[bold]{node.id}[/bold] now mentions agent [bold]{agents}[/bold]")
    elif skills is not None:
        console.print(f"[bold]{node.id}[/bold] now mentions skill [bold]{skills}[/bold]")
    elif trains is not None:
        console.print(f"[bold]{node.id}[/bold] now trains [bold]{trains}[/bold]")
    else:
        console.print(f"[bold]{node.id}[/bold] now links to [bold]{to}[/bold] ({rel})")
