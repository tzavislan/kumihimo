"""
@file        tests/test_store_roundtrip.py
@purpose     The fidelity contract, executable: untouched files are never
             written; touched files keep comments, key order, newline style, and
             BOM; bodies survive byte-for-byte; malformed files become precise
             findings, never crashes.
@layer       tests
@tags        store, round-trip, fidelity, frontmatter, crlf, bom
@related     kumihimo/core/store.py (under test),
             kumihimo/core/plan.py (the facade used to drive it)
@design      PLAN.md §3.3, queue item K2
"""

from pathlib import Path

import pytest

from kumihimo import KumihimoError, Plan
from kumihimo.core import store

MANIFEST = "format: 1\nplan: Fixture\nkinds:\n  from: engineering\n"

NASTY = (
    "---\n"
    "# chosen after the Redis incident\n"
    "kind: task  # inline comment\n"
    'title: "Quoted: title"\n'
    "needs:\n"
    "  - api-endpoints\n"
    "effort: M\n"
    "---\n"
    "Body — line one with unicode 組紐.\n"
    "\n"
    "    indented code block\n"
    "trailing spaces  \n"
)

SIMPLE = "---\nkind: task\n---\nplain body\n"


def make_plan(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "plan"
    (root / "nodes").mkdir(parents=True)
    (root / "kumihimo.yaml").write_bytes(MANIFEST.encode("utf-8"))
    for name, text in files.items():
        target = root / "nodes" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    return root


def test_untouched_plan_saves_nothing_and_bytes_survive(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"nasty.md": NASTY, "api-endpoints.md": SIMPLE})
    plan = Plan.load(root)
    assert plan.save() == []
    assert (root / "nodes" / "nasty.md").read_bytes() == NASTY.encode("utf-8")
    assert (root / "nodes" / "api-endpoints.md").read_bytes() == SIMPLE.encode("utf-8")


def test_field_edit_keeps_comments_body_and_neighbors(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"nasty.md": NASTY, "api-endpoints.md": SIMPLE})
    plan = Plan.load(root)
    record = plan.records["nasty"]
    record.fm["effort"] = "L"
    record.dirty = True
    assert plan.save() == ["nodes/nasty.md"]
    text = (root / "nodes" / "nasty.md").read_text(encoding="utf-8")
    assert "# chosen after the Redis incident" in text
    assert "kind: task  # inline comment" in text
    assert 'title: "Quoted: title"' in text
    assert "effort: L" in text
    body = text.split("---\n", 2)[2]
    assert body == NASTY.split("---\n", 2)[2]
    assert (root / "nodes" / "api-endpoints.md").read_bytes() == SIMPLE.encode("utf-8")


def test_crlf_file_stays_crlf_after_edit(tmp_path: Path) -> None:
    crlf = NASTY.replace("\n", "\r\n")
    root = make_plan(tmp_path, {"nasty.md": crlf})
    plan = Plan.load(root)
    record = plan.records["nasty"]
    record.fm["effort"] = "L"
    record.dirty = True
    plan.save()
    data = (root / "nodes" / "nasty.md").read_bytes()
    expected = crlf.replace("effort: M", "effort: L").encode("utf-8")
    assert data == expected


def test_bom_survives_an_edit(tmp_path: Path) -> None:
    # The string below starts with a literal, invisible U+FEFF byte-order mark.
    root = make_plan(tmp_path, {"bommed.md": "﻿" + SIMPLE})
    plan = Plan.load(root)
    record = plan.records["bommed"]
    record.fm["status"] = "doing"
    record.dirty = True
    plan.save()
    assert (root / "nodes" / "bommed.md").read_bytes().startswith(b"\xef\xbb\xbf")


def test_subfolder_ids_and_default_titles(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"auth/login-flow.md": SIMPLE})
    plan = Plan.load(root)
    assert "auth/login-flow" in plan.nodes
    assert plan.nodes["auth/login-flow"].title == "Login flow"


def test_scalar_needs_coerces_and_bad_needs_is_finding(tmp_path: Path) -> None:
    good = "---\nkind: task\nneeds: api\n---\n"
    bad = "---\nkind: task\nneeds: 5\n---\n"
    root = make_plan(tmp_path, {"good.md": good, "bad.md": bad})
    plan = Plan.load(root)
    assert plan.nodes["good"].needs == ["api"]
    assert any("'needs'" in f.message and f.where == "bad" for f in plan.load_findings)


def test_unterminated_frontmatter_is_finding_and_body_preserved(tmp_path: Path) -> None:
    broken = "---\nkind: task\nno closing delimiter\n"
    root = make_plan(tmp_path, {"broken.md": broken})
    plan = Plan.load(root)
    assert any("unterminated" in f.message for f in plan.load_findings)
    assert plan.save() == []
    assert (root / "nodes" / "broken.md").read_bytes() == broken.encode("utf-8")


def test_invalid_yaml_frontmatter_reports_a_line(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"badyaml.md": "---\nkind: task\nx: [unclosed\n---\nbody\n"})
    plan = Plan.load(root)
    assert any("not valid YAML" in f.message and f.where == "badyaml" for f in plan.load_findings)


def test_non_mapping_frontmatter_is_finding(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"listy.md": "---\n- a\n- b\n---\nbody\n"})
    plan = Plan.load(root)
    assert any("must be a mapping" in f.message for f in plan.load_findings)


def test_uppercase_id_violates_slug_rule(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"BadName.md": SIMPLE})
    plan = Plan.load(root)
    assert any("lowercase" in f.message for f in plan.load_findings)


def test_case_collisions_unit() -> None:
    assert store.case_collisions(["API", "api", "b"]) == ["api"]
    assert store.case_collisions(["a", "b"]) == []


def test_links_parse_strings_and_mappings(tmp_path: Path) -> None:
    text = "---\nkind: task\nlinks:\n  - redis-outage\n  - {to: pick-algo, rel: informs}\n---\n"
    root = make_plan(tmp_path, {"linked.md": text})
    plan = Plan.load(root)
    links = plan.nodes["linked"].links
    assert [(link.to, link.rel) for link in links] == [
        ("redis-outage", "see-also"),
        ("pick-algo", "informs"),
    ]


def test_scaffold_makes_a_loadable_plan_and_refuses_twice(tmp_path: Path) -> None:
    root = store.scaffold(tmp_path / "demo", name="Demo")
    plan = Plan.load(root)
    assert plan.load_findings == []
    assert "first-thread" in plan.nodes
    assert plan.manifest.pack == "engineering"
    with pytest.raises(KumihimoError, match="already"):
        store.scaffold(tmp_path / "demo")


def test_missing_node_raises_clean_error(tmp_path: Path) -> None:
    root = make_plan(tmp_path, {"a.md": SIMPLE})
    plan = Plan.load(root)
    with pytest.raises(KumihimoError, match="no-such"):
        plan.node("no-such")


def test_not_a_plan_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(KumihimoError, match=r"kumihimo\.yaml"):
        Plan.load(tmp_path)
