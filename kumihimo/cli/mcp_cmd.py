"""
@file        kumihimo/cli/mcp_cmd.py
@purpose     `kumihimo mcp` — serve one plan over MCP stdio so an agent can
             inspect, restructure, and braid it. Blocks until the client
             disconnects.
@layer       cli
@tags        cli, mcp, stdio
@related     kumihimo/mcp/server.py (what this runs),
             .mcp.json (wires Claude Code to the roadmap plan)
@design      PLAN.md §6.1
"""

from __future__ import annotations

from pathlib import Path

import typer

from kumihimo.cli.common import die
from kumihimo.core.errors import KumihimoError
from kumihimo.core.store import find_root
from kumihimo.mcp.server import build_server


def mcp(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory to serve."),
) -> None:
    """Serve a plan over MCP (stdio).

    @purpose  The whole ops surface for agents; stdout belongs to the protocol,
              so everything human goes to stderr.
    """
    try:
        root = find_root(plan_path)
    except KumihimoError as err:
        die(str(err))
    build_server(root).run()
