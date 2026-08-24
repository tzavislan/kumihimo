"""
@file        kumihimo/cli/app.py
@purpose     Assembles the Typer application and provides the console entry point;
             owns only --version and help, with each verb registered from its own
             module as milestones land.
@layer       cli
@tags        cli, entry-point, version
@related     kumihimo/__init__.py (the version this prints),
             pyproject.toml ([project.scripts] wires main here)
@design      PLAN.md §1
"""

import typer

import kumihimo
from kumihimo.cli.add_cmd import add
from kumihimo.cli.braid_cmd import braid
from kumihimo.cli.check_cmd import check
from kumihimo.cli.edit_cmd import edit
from kumihimo.cli.export_cmd import export
from kumihimo.cli.link_cmd import link
from kumihimo.cli.mcp_cmd import mcp
from kumihimo.cli.new_cmd import new

app = typer.Typer(
    name="kumihimo",
    help="Braid a plan graph of plain-text files into one well-ordered prompt.",
    no_args_is_help=True,
    add_completion=False,
)

app.command("new")(new)
app.command("add")(add)
app.command("link")(link)
app.command("check")(check)
app.command("braid")(braid)
app.command("export")(export)
app.command("mcp")(mcp)
app.command("edit")(edit)


def _version_callback(value: bool) -> None:
    """Print the version and exit when --version is passed.

    @purpose  Standard eager --version handling, kept out of every verb.
    """
    if value:
        typer.echo(f"kumihimo {kumihimo.__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Print the version."
    ),
) -> None:
    """Root options shared by every verb.

    @purpose  Hosts global flags; verbs are separate commands registered in app.py.
    """


def main() -> None:
    """Console-script entry point.

    @purpose  What [project.scripts] invokes; exists so the Typer app object stays importable
              for tests without running it.
    """
    app()
