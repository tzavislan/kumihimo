"""
@file        tests/test_kinds.py
@purpose     The kind system behaves: packs load, manifest overrides merge and
             extend, bad overrides become findings not crashes, field validation
             is precise per type, and defaults apply without touching files.
@layer       tests
@tags        kinds, packs, field-validation
@related     kumihimo/core/kinds.py (under test),
             kumihimo/packs/engineering/kinds.yaml (the shipped schemas)
@design      PLAN.md §3.2, queue item K1
"""

import pytest

from kumihimo.core.errors import KumihimoError
from kumihimo.core.kinds import (
    effective_fields,
    load_pack,
    resolve_kinds,
    validate_fields,
)
from kumihimo.core.model import FieldSpec, KindDef, Node


def node(**kwargs: object) -> Node:
    return Node.model_validate({"id": "n", "kind": "task", **kwargs})


def test_engineering_pack_loads_with_expected_kinds() -> None:
    kinds = load_pack("engineering")
    assert set(kinds) == {
        "task",
        "milestone",
        "decision",
        "risk",
        "question",
        "agent",
        "skill",
        "reference",
    }
    assert kinds["task"].fields["status"].default == "todo"
    assert kinds["task"].fields["effort"].options == ["S", "M", "L"]
    assert kinds["agent"].fields["runtime"].options == ["claude-code", "cloud", "human", "other"]


def test_crew_kinds_have_no_required_fields() -> None:
    # PLAN2 §3.1: agent/skill/reference stay finding-based, never crash-on-load —
    # a bare `kind: agent` node must still be a valid, loadable node.
    kinds = load_pack("engineering")
    for name in ("agent", "skill", "reference"):
        assert not any(spec.required for spec in kinds[name].fields.values()), name


def test_unknown_pack_raises_and_names_available() -> None:
    with pytest.raises(KumihimoError, match="engineering"):
        load_pack("no-such-pack")


def test_resolve_merges_pack_extension_and_new_kind() -> None:
    overrides = {
        "task": {"fields": {"component": {"type": "str"}}},
        "spike": {"fields": {"timebox": {"type": "str", "required": True}}},
    }
    kinds, findings = resolve_kinds("engineering", overrides)
    assert findings == []
    assert "component" in kinds["task"].fields
    assert "status" in kinds["task"].fields  # pack fields survive the merge
    assert kinds["spike"].fields["timebox"].required is True


def test_resolve_override_replaces_same_named_field_spec() -> None:
    overrides = {"task": {"fields": {"effort": {"type": "choice", "options": ["XS", "XL"]}}}}
    kinds, findings = resolve_kinds("engineering", overrides)
    assert findings == []
    assert kinds["task"].fields["effort"].options == ["XS", "XL"]


def test_resolve_bad_override_is_finding_not_crash() -> None:
    overrides = {
        "task": {"fields": {"x": {"type": "nope"}}},
        "spike": {"fields": {"timebox": {"type": "str"}}},
    }
    kinds, findings = resolve_kinds("engineering", overrides)
    assert any(f.level == "error" and "task" in f.message for f in findings)
    assert "spike" in kinds  # the rest of the manifest still resolves


def test_resolve_non_mapping_override_is_finding() -> None:
    kinds, findings = resolve_kinds("engineering", {"task": "oops"})
    assert any("must be a mapping" in f.message for f in findings)
    assert kinds["task"].fields["status"].default == "todo"  # pack kind unharmed


def test_resolve_unknown_pack_is_finding() -> None:
    _, findings = resolve_kinds("no-such", {})
    assert any(f.level == "error" and "unknown kind pack" in f.message for f in findings)


def test_choice_validation_names_the_options() -> None:
    kinds, _ = resolve_kinds("engineering", {})
    findings = validate_fields(node(fields={"effort": "XL"}), kinds["task"])
    assert len(findings) == 1
    assert "S, M, L" in findings[0].message
    assert "XL" in findings[0].message


def test_int_rejects_bool_and_list_rejects_non_strings() -> None:
    kind = KindDef(
        name="k",
        fields={"n": FieldSpec(type="int"), "items": FieldSpec(type="list")},
    )
    assert validate_fields(node(fields={"n": True}), kind)[0].level == "error"
    assert validate_fields(node(fields={"n": 3}), kind) == []
    assert "list of strings" in validate_fields(node(fields={"items": [1]}), kind)[0].message
    assert validate_fields(node(fields={"items": ["a"]}), kind) == []


def test_required_without_default_is_error_with_default_is_not() -> None:
    kind = KindDef(
        name="k",
        fields={
            "must": FieldSpec(type="str", required=True),
            "soft": FieldSpec(type="str", required=True, default="x"),
        },
    )
    findings = validate_fields(node(), kind)
    assert [f.message for f in findings] == ["missing required field 'must'"]


def test_undeclared_field_is_warning() -> None:
    kinds, _ = resolve_kinds("engineering", {})
    findings = validate_fields(node(fields={"efort": "M"}), kinds["task"])
    assert findings[0].level == "warning"
    assert "efort" in findings[0].message


def test_effective_fields_fill_defaults_without_overriding_given() -> None:
    kinds, _ = resolve_kinds("engineering", {})
    assert effective_fields(node(), kinds["task"])["status"] == "todo"
    assert effective_fields(node(fields={"status": "done"}), kinds["task"])["status"] == "done"
