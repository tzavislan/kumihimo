"""
@file        tests/test_lint.py
@purpose     Behaviour coverage for every conventions-linter check: the cap and
             its counting rules, the @exempt grammar, header tags, public
             @purpose, and README index generation — including what --fix must
             refuse to do.
@layer       tests
@tags        lint, conventions, fixtures
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
