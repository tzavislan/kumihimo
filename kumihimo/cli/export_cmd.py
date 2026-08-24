"""
@file        kumihimo/cli/export_cmd.py
@purpose     `kumihimo export` — the plan as a diagram source: Mermaid (GitHub
             renders it natively) or Graphviz DOT, to stdout or a file.
@layer       cli
@tags        cli, export, mermaid, dot
@related     kumihimo/compile/export.py (generates what this writes)
@design      PLAN.md §9 M2
"""

from __future__ import annotations

from pathlib import Path

import typer

from kumihimo.cli.common import die, err_console, write_artifact
from kumihimo.compile import export as export_module
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan


def export(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    fmt: str = typer.Option("mermaid", "--format", help="mermaid or dot."),
    out: Path | None = typer.Option(None, "-o", "--out", help="Write to a file instead of stdout."),
) -> None:
    """Export the plan graph as diagram source.

    @purpose  The picture without the prompt — for READMEs, docs, and Graphviz.
    """
    try:
        plan = Plan.load(plan_path)
        if fmt == "mermaid":
            text = export_module.mermaid(plan) + "\n"
        elif fmt == "dot":
            text = export_module.dot(plan) + "\n"
        else:
            raise KumihimoError(f"unknown format '{fmt}' (mermaid, dot)")
    except KumihimoError as err:
        die(str(err))
    if out is not None:
        out.write_bytes(text.encode("utf-8"))
        err_console.print(f"exported {fmt} to {out}")
    else:
        write_artifact(text)
