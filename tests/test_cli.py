"""
@file        tests/test_cli.py
@purpose     The installed command behaves at the surface: --version prints the
             package version, and a bare invocation shows help without erroring.
@layer       tests
@tags        cli, version, smoke
@related     kumihimo/cli/app.py (the app under test)
@design      PLAN.md §9 M0
"""

from typer.testing import CliRunner

import kumihimo
from kumihimo.cli.app import app

runner = CliRunner()


def test_version_flag_prints_package_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert kumihimo.__version__ in result.output


def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])
    # Click 8.2+ exits 2 for no-args-shows-help; the contract we care about is
    # help text, not a traceback.
    assert result.exit_code in (0, 2)
    assert "Usage" in result.output
