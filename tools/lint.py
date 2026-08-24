"""
@file        tools/lint.py
@purpose     Enforces the repo conventions in CI: the 600-code-line file cap with
             the @exempt escape, the @file/@purpose docstring tag scheme, and
             per-folder READMEs whose generated index stays true. Reports, without
             failing, current exemptions and the ten largest files. The Yorishiro
             lesson this file exists for: rules nobody enforces rot.
@layer       tools
@tags        lint, conventions, file-cap, tags, readme-index, ci
@related     CONVENTIONS.md (the rules in prose),
             tests/test_lint.py (behaviour coverage for every check)
@design      PLAN.md §7.3
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

CAP = 600
SCAN_ROOTS = ("kumihimo", "tools", "tests")
EXCLUDE_DIRS = {"__pycache__", ".venv", "node_modules", "static"}
EXEMPT_RULES = {"file-size"}
INDEX_BEGIN = "<!-- BEGIN GENERATED INDEX -- do not edit by hand -->"
INDEX_END = "<!-- END GENERATED INDEX -->"
EXEMPT_RE = re.compile(r"^\s*@exempt\s+(\S+)\s+reviewer=(\S+)\s+reason=(\S.*)$")
TAG_RE = re.compile(r"^\s*@([a-z]+)\s+(\S.*)$")
PURPOSE_TRUNCATE = 160


@dataclass
class Violation:
    """A single rule breach at a path.

    @purpose  The unit of failure: one path, one human-readable message.
    """

    path: str
    message: str


@dataclass
class Exemption:
    """A parsed @exempt declaration.

    @purpose  Carries rule, reviewer, and reason so every run can report exemptions
              and they never accumulate quietly.
    """

    path: str
    rule: str
    reviewer: str
    reason: str
    stale: bool


@dataclass
class LintResult:
    """Everything one lint run found.

    @purpose  Single return value so tests and main() share the exact same view.
    """

    violations: list[Violation]
    exemptions: list[Exemption]
    largest: list[tuple[int, str]]
    fixed: list[str]


@dataclass
class _FileFacts:
    """Parsed facts about one Python file, computed once and reused by every check."""

    path: Path
    rel: str
    code_lines: int
    tags: dict[str, str]
    exempt_rules: set[str]


def iter_py_files(repo: Path) -> list[Path]:
    """List every Python file the linter owns, in stable order.

    @purpose  One shared discovery walk so every check sees the same tree; excludes
              caches, venvs, and built assets.
    """
    found: list[Path] = []
    for root in SCAN_ROOTS:
        base = repo / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if not EXCLUDE_DIRS.intersection(p.name for p in path.parents):
                found.append(path)
    return found


def _docstring_lines(tree: ast.Module) -> set[int]:
    """Line numbers occupied by module/class/function docstrings.

    @purpose  Docstrings are documentation, and documentation never fights the cap.
    """
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            end = body[0].value.end_lineno or body[0].value.lineno
            lines.update(range(body[0].value.lineno, end + 1))
    return lines


def count_code_lines(source: str, tree: ast.Module) -> int:
    """Count lines that are neither blank, comment-only, nor docstring.

    @purpose  Implements the cap's definition of "code line" so heavy commenting
              never fights the 600 limit.
    @tags     file-cap, counting
    """
    physical = source.splitlines()
    excluded: set[int] = {i for i, line in enumerate(physical, 1) if not line.strip()}
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and physical[tok.start[0] - 1].lstrip().startswith("#"):
            excluded.add(tok.start[0])
    excluded |= _docstring_lines(tree)
    return len(set(range(1, len(physical) + 1)) - excluded)


def parse_tags(docstring: str | None) -> dict[str, str]:
    """Parse @tag values from a docstring, joining wrapped continuation lines.

    @purpose  One parser for the tag scheme, shared by the header check and the
              README index generator.
    """
    tags: dict[str, str] = {}
    current: str | None = None
    for raw in (docstring or "").splitlines():
        match = TAG_RE.match(raw)
        if match:
            current = match.group(1)
            tags[current] = match.group(2).strip()
        elif current and raw.strip():
            tags[current] += " " + raw.strip()
        else:
            current = None
    return tags


def _parse_exemptions(docstring: str | None, rel: str, violations: list[Violation]) -> set[str]:
    """Extract valid @exempt rules from a header, flagging malformed or unknown ones.

    @purpose  Enforces the fixed @exempt grammar so exemptions stay auditable.
    """
    rules: set[str] = set()
    for raw in (docstring or "").splitlines():
        # A declaration starts its line; prose that merely mentions @exempt is not one.
        if not raw.lstrip().startswith("@exempt"):
            continue
        match = EXEMPT_RE.match(raw)
        if not match:
            grammar = "@exempt <rule> reviewer=<name> reason=<text>"
            violations.append(Violation(rel, f"malformed @exempt (grammar: {grammar})"))
        elif match.group(1) not in EXEMPT_RULES:
            violations.append(Violation(rel, f"@exempt names unknown rule '{match.group(1)}'"))
        else:
            rules.add(match.group(1))
    return rules


def _check_public_purposes(tree: ast.Module, rel: str, violations: list[Violation]) -> None:
    """Require @purpose on every public module-level or class-level def.

    @purpose  The tag scheme is what makes grep a working index; a public item
              without @purpose is invisible to it.
    """

    def visit(items: list[ast.stmt]) -> None:
        """Check one body's defs and recurse into class bodies.

        @purpose  Depth-limited walk: module and class level only, since nested
                  helper functions are not public interface.
        """
        for node in items:
            if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                if not node.name.startswith("_"):
                    doc = ast.get_docstring(node, clean=False)
                    if not doc or "@purpose" not in doc:
                        violations.append(
                            Violation(
                                rel,
                                f"public item '{node.name}' (line {node.lineno}) has no @purpose",
                            )
                        )
                if isinstance(node, ast.ClassDef):
                    visit(node.body)

    visit(tree.body)


def _gather_facts(path: Path, repo: Path, violations: list[Violation]) -> _FileFacts | None:
    """Parse one file and run its per-file checks.

    @purpose  Single pass per file: header presence, @file path match, cap count,
              exemptions, and (outside tests/) public @purpose coverage.
    """
    rel = path.relative_to(repo).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as err:
        violations.append(Violation(rel, f"cannot parse: {err}"))
        return None
    doc = ast.get_docstring(tree, clean=False)
    tags = parse_tags(doc)
    if "file" not in tags or "purpose" not in tags:
        violations.append(Violation(rel, "missing @file/@purpose header docstring"))
    elif tags["file"] != rel:
        mismatch = f"@file header ({tags['file']}) does not match path ({rel})"
        violations.append(Violation(rel, mismatch))
    if not rel.startswith("tests/"):
        _check_public_purposes(tree, rel, violations)
    return _FileFacts(
        path=path,
        rel=rel,
        code_lines=count_code_lines(source, tree),
        tags=tags,
        exempt_rules=_parse_exemptions(doc, rel, violations),
    )


def _index_table(folder_facts: list[_FileFacts]) -> str:
    """Render the generated README index for one folder's files.

    @purpose  The machine-maintained half of every folder README, built from the
              files' own @purpose lines so it cannot drift from the code.
    """
    rows = ["| file | purpose |", "|---|---|"]
    for facts in sorted(folder_facts, key=lambda f: f.path.name):
        purpose = " ".join(facts.tags.get("purpose", "(no @purpose)").split())
        if len(purpose) > PURPOSE_TRUNCATE:
            purpose = purpose[: PURPOSE_TRUNCATE - 1] + "…"
        rows.append(f"| `{facts.path.name}` | {purpose} |")
    return "\n".join(rows)


def _check_readme(
    folder: Path, repo: Path, table: str, fix: bool, violations: list[Violation], fixed: list[str]
) -> None:
    """Verify one folder's README exists and its generated index is current.

    @purpose  Keeps the map beside the territory. --fix regenerates a stale index
              but never invents a missing README — prose is hand-written or absent.
    """
    rel = folder.relative_to(repo).as_posix() + "/README.md"
    readme = folder / "README.md"
    if not readme.exists():
        violations.append(Violation(rel, "folder has .py files but no README.md"))
        return
    text = readme.read_text(encoding="utf-8")
    if text.count(INDEX_BEGIN) != 1 or text.count(INDEX_END) != 1:
        violations.append(Violation(rel, "index markers missing, duplicated, or malformed"))
        return
    pre, _, rest = text.partition(INDEX_BEGIN)
    if INDEX_END in pre:
        violations.append(Violation(rel, "index markers out of order"))
        return
    mid, _, post = rest.partition(INDEX_END)
    if mid.strip() == table:
        return
    if fix:
        rebuilt = pre + INDEX_BEGIN + "\n" + table + "\n" + INDEX_END + post
        readme.write_text(rebuilt, encoding="utf-8")
        fixed.append(rel)
    else:
        violations.append(Violation(rel, "generated index is stale (run tools/lint.py --fix)"))


def run(repo: Path, fix: bool = False) -> LintResult:
    """Run every check over the repo and return everything found.

    @purpose  The whole linter behind one call, so tests and main() cannot diverge.
    @tags     lint, entry
    """
    violations: list[Violation] = []
    fixed: list[str] = []
    all_facts: list[_FileFacts] = []
    for path in iter_py_files(repo):
        facts = _gather_facts(path, repo, violations)
        if facts is not None:
            all_facts.append(facts)

    exemptions: list[Exemption] = []
    for facts in all_facts:
        exempt = "file-size" in facts.exempt_rules
        if exempt:
            reviewer, reason = _exempt_details(facts)
            exemptions.append(
                Exemption(facts.rel, "file-size", reviewer, reason, stale=facts.code_lines <= CAP)
            )
        if facts.code_lines > CAP and not exempt:
            violations.append(
                Violation(facts.rel, f"{facts.code_lines} code lines exceeds the {CAP}-line cap")
            )

    by_folder: dict[Path, list[_FileFacts]] = {}
    for facts in all_facts:
        by_folder.setdefault(facts.path.parent, []).append(facts)
    for folder, folder_facts in sorted(by_folder.items()):
        _check_readme(folder, repo, _index_table(folder_facts), fix, violations, fixed)

    largest = sorted(((f.code_lines, f.rel) for f in all_facts), reverse=True)[:10]
    violations.sort(key=lambda v: (v.path, v.message))
    return LintResult(violations, exemptions, largest, fixed)


def _exempt_details(facts: _FileFacts) -> tuple[str, str]:
    """Pull reviewer and reason back out of a file's @exempt line for reporting.

    @purpose  Reports name who approved what, so exemptions stay visible decisions.
    """
    doc = facts.path.read_text(encoding="utf-8")
    for raw in doc.splitlines():
        match = EXEMPT_RE.match(raw)
        if match:
            return match.group(2), match.group(3).strip()
    return "?", "?"


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper: print findings and reports, exit 1 on violations.

    @purpose  What CI runs; --fix regenerates stale README indexes in place.
    """
    parser = argparse.ArgumentParser(description="Kumihimo conventions linter.")
    parser.add_argument("--fix", action="store_true", help="regenerate stale README indexes")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    result = run(args.repo, fix=args.fix)

    for fixed in result.fixed:
        print(f"fixed: regenerated index in {fixed}")
    for violation in result.violations:
        print(f"FAIL {violation.path}: {violation.message}")
    if result.exemptions:
        print("-- exemptions --")
        for ex in result.exemptions:
            note = " (file now under cap; exemption removable)" if ex.stale else ""
            print(f"   {ex.path}: {ex.rule} reviewer={ex.reviewer} reason={ex.reason}{note}")
    print("-- largest files (code lines) --")
    for count, rel in result.largest:
        print(f"   {count:5d}  {rel}")
    if result.violations:
        print(f"{len(result.violations)} violation(s).")
        return 1
    print("conventions clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
