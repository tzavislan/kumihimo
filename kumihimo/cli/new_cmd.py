"""
@file        kumihimo/cli/new_cmd.py
@purpose     `kumihimo new` — scaffold a plan directory with the engineering
             pack and a starter node, then say what to do next.
@layer       cli
@tags        cli, new, scaffold
@related     kumihimo/core/store.py (scaffold does the work)
@design      PLAN.md §1
"""

from __future__ import annotations

from pathlib import Path

import typer

from kumihimo.cli.common import console, die
from kumihimo.core import store
from kumihimo.core.errors import KumihimoError


def new(
    path: Path = typer.Argument(..., help="Directory to create the plan in."),
    name: str | None = typer.Option(None, "--name", help="Plan name (default: directory name)."),
) -> None:
    """Create a new plan with the engineering starter kinds.

    @purpose  The first ten-minute-story step: one command, a working plan.
    """
    try:
        root = store.scaffold(path, name=name)
    except KumihimoError as err:
        die(str(err))
    console.print(f"braided a new plan at [bold]{root}[/bold]")
    console.print(f'next: [dim]kumihimo add {path} <id> --kind task --body "..."[/dim]')
    console.print(f"      [dim]kumihimo check {path}[/dim]")
