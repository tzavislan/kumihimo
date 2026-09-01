"""
@file        tests/test_lint.py
@purpose     Behaviour coverage for every conventions-linter check: the cap and
             its counting rules, the exemption grammar, header tags, public
             purpose coverage, and README index generation — including what
             --fix must refuse to do. Mirrored below, in the test_ts_* group,
             for the TypeScript checks: header, cap, exemptions, README index.
             No TS mirror of the per-function purpose tests exists, since that
             rule stays Python-only.
@layer       tests
@tags        lint, conventions, fixtures, typescript
@related     tools/lint.py (the linter under test)
@design      PLAN.md §7.3
"""

from pathlib import Path

from tools import lint

HEADER = '"""\n@file        kumihimo/{name}\n@purpose     {purpose}\n{extra}"""\n'


def write_module(
    repo: Path,
    name: str,
    purpose: str = "Does one test-fixture thing.",
    body: str = "",
    extra: str = "",
    header: bool = True,
) -> Path:
    path = repo / "kumihimo" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    head = HEADER.format(name=name, purpose=purpose, extra=extra) if header else ""
    path.write_text(head + body, encoding="utf-8")
    return path


TS_HEADER = "/**\n * @file        frontend/src/{name}\n * @purpose     {purpose}\n{extra} */\n"


def write_ts_module(
    repo: Path,
    name: str,
    purpose: str = "Does one test-fixture thing.",
    body: str = "",
    extra: str = "",
    header: bool = True,
) -> Path:
    path = repo / "frontend" / "src" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    head = TS_HEADER.format(name=name, purpose=purpose, extra=extra) if header else ""
    path.write_text(head + body, encoding="utf-8")
    return path


def write_readme(repo: Path, folder: str = "kumihimo", middle: str = "\n") -> Path:
    path = repo / folder / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"# fixture\n\n{lint.INDEX_BEGIN}{middle}{lint.INDEX_END}\n\n## Prose\nHand-written.\n"
    path.write_text(text, encoding="utf-8")
    return path


def messages(repo: Path, fix: bool = False) -> list[str]:
    result = lint.run(repo, fix=fix)
    return [f"{v.path}: {v.message}" for v in result.violations]


def test_clean_tree_passes_after_fix_generates_index(tmp_path: Path) -> None:
    write_module(tmp_path, "a.py", body="x = 1\n")
    write_readme(tmp_path)
    assert lint.run(tmp_path, fix=True).fixed == ["kumihimo/README.md"]
    assert messages(tmp_path) == []


def test_file_over_cap_fails(tmp_path: Path) -> None:
    write_module(tmp_path, "big.py", body="x = 0\n" * (lint.CAP + 1))
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    assert any("exceeds" in m for m in messages(tmp_path))


def test_comments_and_docstrings_do_not_count(tmp_path: Path) -> None:
    body = "# comment\n" * (lint.CAP + 100) + "x = 1\n"
    write_module(tmp_path, "chatty.py", body=body)
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    assert messages(tmp_path) == []


def test_exempt_file_passes_and_is_reported(tmp_path: Path) -> None:
    extra = "@exempt file-size reviewer=thomas reason=test fixture over the cap\n"
    write_module(tmp_path, "big.py", body="x = 0\n" * (lint.CAP + 1), extra=extra)
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    result = lint.run(tmp_path)
    assert [f"{v.path}: {v.message}" for v in result.violations] == []
    assert len(result.exemptions) == 1
    assert result.exemptions[0].reviewer == "thomas"
    assert result.exemptions[0].stale is False


def test_exemption_on_small_file_is_marked_stale(tmp_path: Path) -> None:
    extra = "@exempt file-size reviewer=thomas reason=no longer needed\n"
    write_module(tmp_path, "small.py", body="x = 1\n", extra=extra)
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    result = lint.run(tmp_path)
    assert result.exemptions[0].stale is True
    assert [f"{v.path}: {v.message}" for v in result.violations] == []


def test_malformed_exempt_fails(tmp_path: Path) -> None:
    write_module(tmp_path, "a.py", body="x = 1\n", extra="@exempt file-size reason=no reviewer\n")
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    assert any("malformed @exempt" in m for m in messages(tmp_path))


def test_unknown_exempt_rule_fails(tmp_path: Path) -> None:
    write_module(tmp_path, "a.py", body="x = 1\n", extra="@exempt no-such reviewer=t reason=r\n")
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    assert any("unknown rule" in m for m in messages(tmp_path))


def test_missing_header_fails(tmp_path: Path) -> None:
    write_module(tmp_path, "bare.py", body="x = 1\n", header=False)
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    assert any("missing @file/@purpose" in m for m in messages(tmp_path))


def test_header_path_mismatch_fails(tmp_path: Path) -> None:
    path = tmp_path / "kumihimo" / "real.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('"""\n@file kumihimo/other.py\n@purpose Wrong path.\n"""\n', encoding="utf-8")
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    assert any("does not match" in m for m in messages(tmp_path))


def test_public_item_without_purpose_fails_and_private_passes(tmp_path: Path) -> None:
    body = (
        'def visible():\n    """No tag here."""\n    return 1\n\n\ndef _hidden():\n    return 2\n'
    )
    write_module(tmp_path, "items.py", body=body)
    write_readme(tmp_path)
    lint.run(tmp_path, fix=True)
    found = messages(tmp_path)
    assert any("'visible'" in m for m in found)
    assert not any("_hidden" in m for m in found)


def test_test_files_skip_item_purpose_but_need_header(tmp_path: Path) -> None:
    path = tmp_path / "tests" / "test_x.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '"""\n@file tests/test_x.py\n@purpose Fixture.\n"""\n\n\ndef test_a():\n    assert True\n',
        encoding="utf-8",
    )
    write_readme(tmp_path, folder="tests")
    lint.run(tmp_path, fix=True)
    assert messages(tmp_path) == []
    path.write_text("def test_a():\n    assert True\n", encoding="utf-8")
    assert any("missing @file/@purpose" in m for m in messages(tmp_path))


def test_missing_readme_fails_and_fix_never_creates_it(tmp_path: Path) -> None:
    write_module(tmp_path, "a.py", body="x = 1\n")
    assert any("no README.md" in m for m in messages(tmp_path, fix=True))
    assert not (tmp_path / "kumihimo" / "README.md").exists()


def test_stale_index_fails_then_fix_rewrites_preserving_prose(tmp_path: Path) -> None:
    write_module(tmp_path, "a.py", purpose="Fixture purpose sentence.", body="x = 1\n")
    readme = write_readme(tmp_path, middle="\n| stale | rows |\n")
    assert any("stale" in m for m in messages(tmp_path))
    result = lint.run(tmp_path, fix=True)
    assert result.fixed == ["kumihimo/README.md"]
    text = readme.read_text(encoding="utf-8")
    assert "Fixture purpose sentence." in text
    assert "Hand-written." in text
    assert "stale | rows" not in text
    assert messages(tmp_path) == []


def test_malformed_markers_fail_and_fix_refuses(tmp_path: Path) -> None:
    write_module(tmp_path, "a.py", body="x = 1\n")
    readme = tmp_path / "kumihimo" / "README.md"
    readme.write_text(f"# fixture\n{lint.INDEX_BEGIN}\nno end marker\n", encoding="utf-8")
    before = readme.read_text(encoding="utf-8")
    result = lint.run(tmp_path, fix=True)
    assert any("markers" in v.message for v in result.violations)
    assert result.fixed == []
    assert readme.read_text(encoding="utf-8") == before


# -- TypeScript mirror --------------------------------------------------------
# Same checks, a JSDoc /** */ header instead of a Python docstring, and a
# frontend/src/ fixture root instead of kumihimo/. No per-function @purpose
# rule exists for TS (see module docstring), so there is no TS counterpart to
# test_public_item_without_purpose_fails_and_private_passes.


def test_ts_clean_tree_passes_after_fix_generates_index(tmp_path: Path) -> None:
    write_ts_module(tmp_path, "a.ts", body="export const x = 1;\n")
    write_readme(tmp_path, folder="frontend/src")
    assert lint.run(tmp_path, fix=True).fixed == ["frontend/src/README.md"]
    assert messages(tmp_path) == []


def test_ts_top_level_config_is_scanned(tmp_path: Path) -> None:
    path = tmp_path / "frontend" / "vite.config.ts"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "/**\n * @file        frontend/vite.config.ts\n"
        " * @purpose     Fixture build config.\n */\n"
        "export default {};\n",
        encoding="utf-8",
    )
    write_readme(tmp_path, folder="frontend")
    lint.run(tmp_path, fix=True)
    assert messages(tmp_path) == []


def test_ts_declaration_file_is_scanned(tmp_path: Path) -> None:
    # .d.ts is not excluded — elk.d.ts in the real tree carries a real header
    # and this proves a header-less one is caught exactly like any other file.
    write_ts_module(tmp_path, "types.d.ts", body="export {};\n", header=False)
    write_readme(tmp_path, folder="frontend/src")
    assert any("missing @file/@purpose" in m for m in messages(tmp_path, fix=True))


def test_ts_file_over_cap_fails(tmp_path: Path) -> None:
    body = "export const x = 0;\n" * (lint.CAP + 1)
    write_ts_module(tmp_path, "big.ts", body=body)
    write_readme(tmp_path, folder="frontend/src")
    lint.run(tmp_path, fix=True)
    assert any("exceeds" in m for m in messages(tmp_path))


def test_ts_line_comments_do_not_count(tmp_path: Path) -> None:
    body = "// comment\n" * (lint.CAP + 100) + "export const x = 1;\n"
    write_ts_module(tmp_path, "chatty.ts", body=body)
    write_readme(tmp_path, folder="frontend/src")
    lint.run(tmp_path, fix=True)
    assert messages(tmp_path) == []


def test_ts_block_comment_does_not_count_but_trailing_code_does(tmp_path: Path) -> None:
    # A trailing // after real code still counts (CONVENTIONS.md); only lines
    # entirely inside a /* */ block are excluded.
    block = "/*\n" + ("filler\n" * (lint.CAP + 50)) + "*/\n"
    body = block + "export const x = 1; // trailing note\n"
    write_ts_module(tmp_path, "blocky.ts", body=body)
    write_readme(tmp_path, folder="frontend/src")
    lint.run(tmp_path, fix=True)
    assert messages(tmp_path) == []


def test_ts_exempt_file_passes_and_is_reported(tmp_path: Path) -> None:
    extra = " * @exempt file-size reviewer=thomas reason=test fixture over the cap\n"
    body = "export const x = 0;\n" * (lint.CAP + 1)
    write_ts_module(tmp_path, "big.ts", body=body, extra=extra)
    write_readme(tmp_path, folder="frontend/src")
    lint.run(tmp_path, fix=True)
    result = lint.run(tmp_path)
    assert [f"{v.path}: {v.message}" for v in result.violations] == []
    assert len(result.exemptions) == 1
    assert result.exemptions[0].reviewer == "thomas"
    assert result.exemptions[0].stale is False


def test_ts_missing_header_fails(tmp_path: Path) -> None:
    write_ts_module(tmp_path, "bare.ts", body="export const x = 1;\n", header=False)
    write_readme(tmp_path, folder="frontend/src")
    lint.run(tmp_path, fix=True)
    assert any("missing @file/@purpose" in m for m in messages(tmp_path))


def test_ts_header_path_mismatch_fails(tmp_path: Path) -> None:
    path = tmp_path / "frontend" / "src" / "real.ts"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "/**\n * @file frontend/src/other.ts\n * @purpose Wrong path.\n */\nexport const x = 1;\n",
        encoding="utf-8",
    )
    write_readme(tmp_path, folder="frontend/src")
    lint.run(tmp_path, fix=True)
    assert any("does not match" in m for m in messages(tmp_path))


def test_ts_missing_readme_fails_and_fix_never_creates_it(tmp_path: Path) -> None:
    write_ts_module(tmp_path, "a.ts", body="export const x = 1;\n")
    assert any("no README.md" in m for m in messages(tmp_path, fix=True))
    assert not (tmp_path / "frontend" / "src" / "README.md").exists()


def test_ts_stale_index_fails_then_fix_rewrites_preserving_prose(tmp_path: Path) -> None:
    body = "export const x = 1;\n"
    write_ts_module(tmp_path, "a.ts", purpose="Fixture purpose sentence.", body=body)
    readme = write_readme(tmp_path, folder="frontend/src", middle="\n| stale | rows |\n")
    assert any("stale" in m for m in messages(tmp_path))
    result = lint.run(tmp_path, fix=True)
    assert result.fixed == ["frontend/src/README.md"]
    text = readme.read_text(encoding="utf-8")
    assert "Fixture purpose sentence." in text
    assert "Hand-written." in text
    assert "stale | rows" not in text
    assert messages(tmp_path) == []
