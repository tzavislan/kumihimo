"""
@file        kumihimo/cli/common.py
@purpose     What every verb shares: the stdout/stderr consoles and the one way
             to die — expected errors print as a styled message and exit 2,
             never as a traceback.
@layer       cli
@tags        cli, errors, console
@related     kumihimo/core/errors.py (the errors this renders)
@design      PLAN.md §7.1
"""

from __future__ import annotations

from typing import NoReturn

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def die(message: str) -> NoReturn:
    """Print an error message and exit 2.

    @purpose  The single rendering of every KumihimoError a verb catches.
    """
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(2)
