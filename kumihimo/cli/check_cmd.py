"""
@file        kumihimo/cli/check_cmd.py
@purpose     `kumihimo check` — render every finding as a table, summarize the
             plan, and exit 1 on errors (or on warnings too, under --strict).
@layer       cli
@tags        cli, check, findings
@related     kumihimo/core/validate.py (produces the findings this renders)
@design      PLAN.md §3.4
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kumihimo.cli.common import console, die
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan


def check(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    strict: bool = typer.Option(False, "--strict", help="Warnings also fail."),
) -> None:
    """Validate a plan and report every finding.

    @purpose  The same findings the editor panel and MCP tool see, as a table
              with an exit code scripts can gate on.
    """
    try:
        plan = Plan.load(plan_path)
    except KumihimoError as err:
        die(str(err))
    findings = plan.check()
    if findings:
        table = Table(show_header=True, header_style="bold")
        table.add_column("level")
        table.add_column("where")
        table.add_column("message", overflow="fold")
        for finding in findings:
            style = "red" if finding.level == "error" else "yellow"
            table.add_row(f"[{style}]{finding.level}[/{style}]", finding.where, finding.message)
        console.print(table)
    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = len(findings) - errors
    nodes = len(plan.nodes)
    edges = sum(len(n.needs) + len(n.in_) + len(n.links) for n in plan.nodes.values())
    summary = f"{nodes} node(s), {edges} edge(s): {errors} error(s), {warnings} warning(s)"
    if errors or (strict and warnings):
        console.print(f"[red]{summary}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]{summary}[/green]")
