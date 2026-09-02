"""
@file        kumihimo/cli/crew_cmd.py
@purpose     `kumihimo crew` — list every agent/skill/reference node as a
             plain aligned table: its informative fields, its `trained` date
             (printed verbatim), and how many nodes mention it. No clock: the
             library never judges what's stale, only reports (PLAN2 §3.6).
@layer       cli
@tags        cli, crew, roster
@related     kumihimo/core/crew.py (the shared computation this renders),
             kumihimo/mcp/tools.py (the MCP twin)
@design      PLAN2.md §3.6, queue item K29
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kumihimo.cli.common import console, die
from kumihimo.core import crew as crew_module
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan

_INFO_FIELDS: dict[str, tuple[str, ...]] = {
    "agent": ("runtime", "model", "entry"),
    "skill": ("invocation", "source", "cadence"),
    "reference": ("locator", "retriever"),
}


def _info(entry: crew_module.RosterEntry) -> str:
    """The curated per-kind field summary for one roster row.

    @purpose  All effective fields would crowd a table this narrow; these are
              the ones a reader briefing this crew member wants first.
    """
    keys = _INFO_FIELDS.get(entry.kind, ())
    return " · ".join(f"{key}={entry.fields[key]}" for key in keys if entry.fields.get(key))


def _mentions(entry: crew_module.RosterEntry) -> str:
    """Mention counts as one compact string, e.g. 'agents:2, trains:1'.

    @purpose  Three sparse columns would waste more space than this narrow
              table has; a reference's consult-link count joins the same string.
    """
    parts = [f"{key}:{count}" for key, count in sorted(entry.mentioned_by.items())]
    if entry.consulted_by:
        parts.append(f"consult:{entry.consulted_by}")
    return ", ".join(parts)


def crew(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
) -> None:
    """List every agent, skill, and reference node as a roster.

    @purpose  Who exists, how each is invoked, when each was last trained —
              dates print exactly as written; deciding what counts as stale
              is the reader's call, never this library's.
    """
    try:
        plan = Plan.load(plan_path)
    except KumihimoError as err:
        die(str(err))
    entries = crew_module.roster(plan)
    table = Table(show_header=True, header_style="bold")
    table.add_column("kind")
    table.add_column("id")
    table.add_column("title")
    table.add_column("info", overflow="fold")
    table.add_column("trained")
    table.add_column("mentions")
    for entry in entries:
        table.add_row(
            entry.kind,
            entry.id,
            entry.title,
            _info(entry),
            str(entry.fields.get("trained") or ""),
            _mentions(entry),
        )
    console.print(table)
    console.print(f"{len(entries)} crew member(s)")
