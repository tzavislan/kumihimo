"""
@file        tests/test_example_fieldnotes.py
@purpose     PLAN.md §10.4's test, executable: a deliberately non-engineering
             plan whose kinds live entirely in its manifest (no pack) checks
             clean, braids through its own inline template, and needed zero
             core changes to exist.
@layer       tests
@tags        example, agnostic-core, custom-kinds
@related     examples/fieldnotes (the fixture),
             kumihimo/core/kinds.py (resolve_kinds with pack=None)
@design      PLAN.md §10.4, roadmap item example-nonengineering
"""

from pathlib import Path

from kumihimo import Plan, braid

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "fieldnotes"


def test_fieldnotes_checks_clean_with_manifest_only_kinds() -> None:
    plan = Plan.load(EXAMPLE)
    assert plan.manifest.pack is None  # no pack: every kind comes from the manifest
    assert set(plan.kinds) == {"question", "source", "claim", "section"}
    assert plan.check() == []


def test_fieldnotes_braids_through_its_inline_template() -> None:
    result = braid(Plan.load(EXAMPLE))
    assert "Cite as: Raymond, E. S. (2003)" in result.text  # the manifest template
    assert "confidence: high" in result.text  # default template covers claim
    assert result.text.index("Source: The Art of Unix") < result.text.index(
        "Version control quietly became"
    )
    assert result.order[-1] == "sec-close"
