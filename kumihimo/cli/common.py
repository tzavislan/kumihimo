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

import sys
from typing import NoReturn

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def write_artifact(text: str) -> None:
    """Write compiler output to stdout as UTF-8, whatever the console claims.

    @purpose  Windows consoles default to cp1252, which silently corrupts
              em-dashes and unicode in piped braids — the artifact's bytes are
              the product, so the artifact writer owns its encoding.
    """
    stdout = sys.stdout
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")
    stdout.write(text)


def die(message: str) -> NoReturn:
    """Print an error message and exit 2.

    @purpose  The single rendering of every KumihimoError a verb catches.
    """
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(2)
