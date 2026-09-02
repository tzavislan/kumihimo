"""
@file        tests/test_crew_golden.py
@purpose     The crew braid's byte-identity contract: crew-demo compiled
             grouped (Cast + Assigned/With/Trains + Consult) and compiled
             `--for wright` (the grounding line, the mention-based selection,
             the milestone falling back to *Also part of:*) must equal their
             committed goldens exactly. Companion to test_golden.py, which
             stays apiguard-only and proves K29 changed it zero bytes.
@layer       tests
@tags        golden, determinism, braid, crew, for-agent, cast, consult
@related     tests/golden/crew-demo-grouped.md, tests/golden/crew-demo-for-wright.md,
             tests/fixtures/crew-demo (the plan these braid)
@design      PLAN2.md §3.3, §3.6-3.7, queue item K29
"""

from pathlib import Path

from kumihimo import Plan, braid

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "crew-demo"


def golden(name: str) -> str:
    return (HERE / "golden" / name).read_bytes().decode("utf-8")


def test_crew_demo_loads_clean() -> None:
    # A check error would gate braid entirely — pinned separately so a
    # golden mismatch below can't be confused with a broken fixture.
    assert Plan.load(FIXTURE).check() == []


def test_grouped_braid_has_cast_mentions_and_consult() -> None:
    text = braid(Plan.load(FIXTURE), strategy="grouped").text
    assert text == golden("crew-demo-grouped.md")


def test_for_agent_braid_opens_with_grounding_line() -> None:
    text = braid(Plan.load(FIXTURE), strategy="grouped", for_agent="wright").text
    assert text == golden("crew-demo-for-wright.md")
    assert text.startswith("# Braid: Crew Demo\n*Ground with:*")
