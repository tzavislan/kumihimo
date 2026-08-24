"""
@file        kumihimo/cli/braid_cmd.py
@purpose     `kumihimo braid` — pull the cord: compile a plan (or a slice via
             --where/--from/--until/--in) to stdout or a file, with --dry for
             the order alone. Output goes through plain stdout, never a styled
             console, so pipes and redirects get exact bytes.
@layer       cli
@tags        cli, braid, slicing, dry-run
@related     kumihimo/compile/braid.py (the pipeline this fronts)
@design      PLAN.md §4
"""

from __future__ import annotations

from pathlib import Path

import typer

from kumihimo.cli.common import die, err_console, write_artifact
from kumihimo.compile import braid as braid_pipeline
from kumihimo.core.errors import KumihimoError
from kumihimo.core.plan import Plan


def _parse_where(pairs: list[str]) -> dict[str, str]:
    """Split repeated --where key=value flags.

    @purpose  A malformed pair names itself instead of half-filtering.
    """
    where: dict[str, str] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key:
            die(f"--where wants key=value, got '{pair}'")
        where[key] = value
    return where


def braid(
    plan_path: Path = typer.Argument(..., metavar="PLAN", help="The plan directory."),
    out: Path | None = typer.Option(None, "-o", "--out", help="Write to a file instead of stdout."),
    strategy: str | None = typer.Option(None, "--strategy", help="linear or grouped."),
    where: list[str] = typer.Option([], "--where", help="key=value effective-field filter."),
    from_: str | None = typer.Option(None, "--from", help="This node and everything after it."),
    until: str | None = typer.Option(None, "--until", help="This node and everything it needs."),
    in_: str | None = typer.Option(None, "--in", help="Members of this group, plus the group."),
    diagram: bool | None = typer.Option(
        None, "--diagram/--no-diagram", help="Embed the Mermaid overview (default: manifest)."
    ),
    dry: bool = typer.Option(False, "--dry", help="Print the order without rendering."),
) -> None:
    """Compile a plan into one well-ordered prompt.

    @purpose  The tool's namesake verb; stdout is the artifact, warnings go to
              stderr so redirection stays clean.
    """
    try:
        plan = Plan.load(plan_path)
        result = braid_pipeline(
            plan,
            strategy=strategy,
            where=_parse_where(where),
            from_=from_,
            until=until,
            in_=in_,
            diagram=diagram,
            dry=dry,
        )
    except KumihimoError as err:
        die(str(err))
    for warning in result.warnings:
        err_console.print(f"[yellow]warning:[/yellow] {warning}")
    if out is not None:
        out.write_bytes(result.text.encode("utf-8"))
        err_console.print(f"braided {len(result.order)} node(s) into {out}")
    else:
        write_artifact(result.text)
