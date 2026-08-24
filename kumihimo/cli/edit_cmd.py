"""
@file        kumihimo/cli/edit_cmd.py
@purpose     `kumihimo edit` — serve the plan's live canvas on localhost and
             open the browser. Read-only through M4; the write path is M5.
@layer       cli
@tags        cli, edit, canvas, localhost
@related     kumihimo/server/app.py (the app this runs)
@design      PLAN.md §5.1
"""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

import typer
import uvicorn

from kumihimo.cli.common import die, err_console
from kumihimo.core.errors import KumihimoError
from kumihimo.core.store import find_root
from kumihimo.server.app import build_app


def edit(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    port: int = typer.Option(8720, "--port", help="Localhost port."),
    open_browser: bool = typer.Option(
        True, "--open/--no-open", help="Open the browser once serving."
    ),
) -> None:
    """Open the live canvas for a plan.

    @purpose  See and arrange the graph; the files stay the only truth and the
              canvas follows them. Binds 127.0.0.1 only, by design.
    """
    try:
        root = find_root(plan_path)
    except KumihimoError as err:
        die(str(err))
    url = f"http://127.0.0.1:{port}"
    err_console.print(f"serving [bold]{root.name}[/bold] at {url} (ctrl-c stops)")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    uvicorn.run(build_app(root), host="127.0.0.1", port=port, log_level="warning")
