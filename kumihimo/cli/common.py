"""
@file        kumihimo/cli/common.py
@purpose     What every verb shares: the stdout/stderr consoles and the one way
             to die — expected errors print as a styled message and exit 2,
             never as a traceback.
@layer       cli
@tags        cli, errors, console, encoding
@related     kumihimo/core/errors.py (the errors this renders)
@design      PLAN.md §7.1
"""

from __future__ import annotations

import sys
from typing import NoReturn

import typer
from rich.console import Console

# Windows consoles default to cp1252, which silently corrupts em-dashes and
# other unicode — not just in piped braids (write_artifact's own fix, kept
# below) but in anything rich prints, since Console.file resolves sys.stdout/
# sys.stderr fresh on every write rather than capturing them once. Reconfigure
# both here, before `console`/`err_console` exist, so every verb's styled
# output (crew's "·" separators included) is UTF-8 regardless of the host
# console's codepage. newline="" additionally disables universal-newlines
# translation on write: without it, encoding= alone leaves Python's default
# text-mode behavior in place, and on Windows that silently rewrites every
# "\n" this library ever produces to "\r\n" on the way out — `kumihimo braid
# PLAN > file` would then disagree, byte for byte, with the exact-LF text
# the API and the goldens hold, even though the console read correctly.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", newline="")

console = Console()
err_console = Console(stderr=True)


def write_artifact(text: str) -> None:
    """Write compiler output to stdout as UTF-8, whatever the console claims.

    @purpose  Windows consoles default to cp1252, which silently corrupts
              em-dashes and unicode in piped braids, and Windows' default
              text-mode newline translation rewrites this library's "\n" to
              "\r\n" on the way out — the artifact's bytes are the product,
              so the artifact writer owns both its encoding and its newlines
              (newline="", matching common.py's module-level reconfigure).
              This reconfigure is now redundant with that module-level one
              (both target the same stdout) but stays as a self-contained
              belt-and-braces: this function's contract doesn't depend on
              common.py's import-time side effect to hold.
    """
    stdout = sys.stdout
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", newline="")
    stdout.write(text)


def die(message: str) -> NoReturn:
    """Print an error message and exit 2.

    @purpose  The single rendering of every KumihimoError a verb catches.
    """
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(2)
