"""
@file        kumihimo/cli/export_cmd.py
@purpose     `kumihimo export` — the plan as a diagram source (Mermaid,
             GitHub-native, or Graphviz DOT) or as JSON Lines, the RAG
             ingestion shape (PLAN2 §3.7), to stdout or a file.
@layer       cli
@tags        cli, export, mermaid, dot, jsonl
@related     kumihimo/compile/export.py (generates what this writes)
@design      PLAN.md §9 M2, PLAN2.md §3.7
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
    fmt: str = typer.Option("mermaid", "--format", help="mermaid, dot, or jsonl."),
    out: Path | None = typer.Option(None, "-o", "--out", help="Write to a file instead of stdout."),
) -> None:
    """Export the plan graph as diagram source or as JSON Lines.

    @purpose  The picture without the prompt (mermaid/dot) or the corpus
              without retrieval (jsonl) — Kumihimo exports data, it never
              fetches it (PLAN2 §3.7).
    """
    try:
        plan = Plan.load(plan_path)
        if fmt == "mermaid":
            text = export_module.mermaid(plan) + "\n"
        elif fmt == "dot":
            text = export_module.dot(plan) + "\n"
        elif fmt == "jsonl":
            text = export_module.jsonl(plan)
        else:
            raise KumihimoError(f"unknown format '{fmt}' (mermaid, dot, jsonl)")
    except KumihimoError as err:
        die(str(err))
    if out is not None:
        out.write_bytes(text.encode("utf-8"))
        err_console.print(f"exported {fmt} to {out}")
    else:
        write_artifact(text)
