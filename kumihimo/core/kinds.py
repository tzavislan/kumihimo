"""
@file        kumihimo/core/kinds.py
@purpose     The kind system: loads shipped packs, merges manifest overrides into
             resolved KindDefs, validates node fields against them, and applies
             defaults. This is where node *meaning* is enforced while core stays
             domain-agnostic.
@layer       core
@tags        kinds, packs, field-validation, defaults
@related     kumihimo/packs/engineering/kinds.yaml (the shipped pack),
             kumihimo/core/validate.py (calls validate_fields per node)
@design      PLAN.md §3.1-3.2
"""

from __future__ import annotations

from importlib import resources
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML

from kumihimo.core.errors import KumihimoError
from kumihimo.core.model import FieldSpec, Finding, KindDef, Node

_MANIFEST = "kumihimo.yaml"


def available_packs() -> list[str]:
    """Names of the kind packs shipped inside the package.

    @purpose  Error messages and docs list what exists instead of guessing.
    """
    packs_dir = resources.files("kumihimo") / "packs"
    return sorted(entry.name for entry in packs_dir.iterdir() if entry.is_dir())


def load_pack(name: str) -> dict[str, KindDef]:
    """Load one shipped pack's kind definitions by name.

    @purpose  Packs are copied-in defaults, not a type hierarchy — this returns
              plain KindDefs the manifest may then extend.
    """
    packs_dir = resources.files("kumihimo") / "packs"
    kinds_file = packs_dir / name / "kinds.yaml"
    if not kinds_file.is_file():
        known = ", ".join(available_packs()) or "none"
        raise KumihimoError(f"unknown kind pack '{name}' (shipped packs: {known})")
    raw = YAML(typ="safe").load(kinds_file.read_text(encoding="utf-8")) or {}
    return {k: KindDef.model_validate({"name": k, **(v or {})}) for k, v in raw.items()}


def _spec_error(err: ValidationError) -> str:
    """Compress a pydantic error into one readable line.

    @purpose  Manifest authors get "fields.effort.type: ..." not a wall of JSON.
    """
    parts = []
    for item in err.errors():
        loc = ".".join(str(p) for p in item["loc"])
        parts.append(f"{loc}: {item['msg']}" if loc else item["msg"])
    return "; ".join(parts)


def resolve_kinds(
    pack: str | None, overrides: dict[str, Any]
) -> tuple[dict[str, KindDef], list[Finding]]:
    """Merge a pack with the manifest's kind overrides into the plan's kinds.

    @purpose  One resolution point for "what kinds exist here": pack kinds first,
              then per-kind extension (fields merge by name; template/color
              replace), then wholly new kinds. Bad overrides become findings,
              never crashes — the rest of the plan stays usable.
    @tags     kinds, merge, manifest
    """
    findings: list[Finding] = []
    kinds: dict[str, KindDef] = {}
    if pack is not None:
        try:
            kinds = load_pack(pack)
        except KumihimoError as err:
            findings.append(Finding(level="error", where=_MANIFEST, message=str(err)))
    for name, raw in overrides.items():
        if not isinstance(raw, dict):
            message = f"kind '{name}' must be a mapping"
            findings.append(Finding(level="error", where=_MANIFEST, message=message))
            continue
        try:
            override = KindDef.model_validate({"name": name, **raw})
        except ValidationError as err:
            message = f"kind '{name}': {_spec_error(err)}"
            findings.append(Finding(level="error", where=_MANIFEST, message=message))
            continue
        base = kinds.get(name)
        if base is None:
            kinds[name] = override
        else:
            kinds[name] = KindDef(
                name=name,
                fields={**base.fields, **override.fields},
                template=override.template or base.template,
                color=override.color or base.color,
            )
    return kinds, findings


def _value_error(spec: FieldSpec, value: Any) -> str | None:
    """Why a value fails its spec, or None when it fits.

    @purpose  Precise per-type messages so `check` output names the fix.
    """
    if spec.type == "str" and not isinstance(value, str):
        return f"expects text, got {value!r}"
    if spec.type == "int" and (isinstance(value, bool) or not isinstance(value, int)):
        return f"expects an integer, got {value!r}"
    if spec.type == "bool" and not isinstance(value, bool):
        return f"expects true/false, got {value!r}"
    if spec.type == "list" and (
        not isinstance(value, list) or any(not isinstance(item, str) for item in value)
    ):
        return f"expects a list of strings, got {value!r}"
    if spec.type == "choice" and (not isinstance(value, str) or value not in spec.options):
        return f"expects one of [{', '.join(spec.options)}], got {value!r}"
    return None


def validate_fields(node: Node, kind: KindDef) -> list[Finding]:
    """Check one node's field bag against its kind's schemas.

    @purpose  The per-node half of `check`: required-without-default, type and
              choice mismatches as errors; fields the kind never declared as
              warnings (typo-catching without breaking forward compatibility).
    @tags     field-validation, findings
    """
    findings: list[Finding] = []
    for name, spec in kind.fields.items():
        if name in node.fields:
            problem = _value_error(spec, node.fields[name])
            if problem:
                message = f"field '{name}' {problem}"
                findings.append(Finding(level="error", where=node.id, message=message))
        elif spec.required and spec.default is None:
            message = f"missing required field '{name}'"
            findings.append(Finding(level="error", where=node.id, message=message))
    for name in node.fields:
        if name not in kind.fields:
            message = f"field '{name}' is not declared by kind '{kind.name}'"
            findings.append(Finding(level="warning", where=node.id, message=message))
    return findings


def effective_fields(node: Node, kind: KindDef) -> dict[str, Any]:
    """The node's fields with the kind's defaults filled in.

    @purpose  Defaults live in memory, never written into the user's file —
              templates and filters see the effective values.
    """
    merged = {name: spec.default for name, spec in kind.fields.items() if spec.default is not None}
    merged.update(node.fields)
    return merged
