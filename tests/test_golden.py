"""
@file        tests/test_golden.py
@purpose     The braid's byte-identity contract: apiguard compiled with each
             strategy must equal the committed golden exactly. A template change
             that alters output must update the golden — and that diff is part
             of the review, read like code.
@layer       tests
@tags        golden, determinism, braid
@related     tests/golden (the committed artifacts),
             kumihimo/packs/engineering/templates (what usually changes them)
@design      PLAN.md §7.1 invariant 4, queue item K9
"""

from pathlib import Path

from kumihimo import Plan, braid

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parent / "examples" / "apiguard"


def golden(name: str) -> str:
    return (HERE / "golden" / name).read_bytes().decode("utf-8")


def test_grouped_braid_matches_golden_exactly() -> None:
    assert braid(Plan.load(EXAMPLE), strategy="grouped").text == golden("apiguard-grouped.md")


def test_linear_braid_matches_golden_exactly() -> None:
    assert braid(Plan.load(EXAMPLE), strategy="linear").text == golden("apiguard-linear.md")
