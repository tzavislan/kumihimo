"""
@file        kumihimo/core/model.py
@purpose     The pure data model: nodes with their two semantic edge kinds and
             annotation links, findings, field specs, kind definitions, and the
             manifest. No IO, no behaviour beyond validation and defaults.
@layer       core
@tags        model, node, edges, kinds, manifest, findings
@related     kumihimo/core/store.py (reads/writes these from disk),
             kumihimo/core/kinds.py (resolves and validates kind fields)
@design      PLAN.md §3.1-3.2
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")

# Frontmatter keys the core owns; everything else is a kind-defined field.
RESERVED_KEYS = ("kind", "title", "needs", "in", "links", "priority")

FORMAT_VERSION = 1


class Link(BaseModel):
    """An annotation edge: free-form relation, zero compiler semantics.

    @purpose  The pressure valve of the model — any relationship users invent fits
              here without core changes (PLAN.md §3.1).
    """

    model_config = ConfigDict(extra="forbid")

    to: str
    rel: str = "see-also"


class Node(BaseModel):
    """One thread of the braid: identity, prose, order, membership, annotation.

    @purpose  The five things core understands about a node; everything else lives
              in the kind-validated `fields` bag.
    @tags     node, needs, membership
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    kind: str = ""
    title: str = ""
    needs: list[str] = Field(default_factory=list)
    in_: list[str] = Field(default_factory=list, alias="in")
    links: list[Link] = Field(default_factory=list)
    priority: int = 0
    fields: dict[str, Any] = Field(default_factory=dict)
    body: str = ""


class Finding(BaseModel):
    """One validation result, error or warning, tied to where it was found.

    @purpose  The unit `check` returns everywhere — CLI table, editor panel, MCP —
              so every surface reports identically.
    """

    level: Literal["error", "warning"]
    where: str
    message: str

    def render(self) -> str:
        """One-line human form.

        @purpose  Shared formatting so CLI and logs agree.
        """
        return f"{self.level}: {self.where}: {self.message}"


class FieldSpec(BaseModel):
    """Schema for one kind-defined field.

    @purpose  Small enough to author by hand in YAML, rich enough to drive
              validation now and editor forms/JSON Schema later.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["str", "int", "bool", "list", "choice"] = "str"
    options: list[str] = Field(default_factory=list)
    required: bool = False
    default: Any = None


class KindDef(BaseModel):
    """A node kind: its field schemas and (from M2) its render template.

    @purpose  Where node *meaning* lives, per the generic/opinionated line —
              the compiler never reads these fields directly, templates do.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    fields: dict[str, FieldSpec] = Field(default_factory=dict)
    template: str | None = None
    color: str | None = None


class CompileSettings(BaseModel):
    """Plan-level braid defaults from the manifest.

    @purpose  The user's standing answers to "how should this compile" so the CLI
              flags are overrides, not requirements.
    """

    model_config = ConfigDict(extra="forbid")

    strategy: str = "grouped"
    preamble: str = ""
    epilogue: str = ""
    diagram: bool = True


class Manifest(BaseModel):
    """Parsed kumihimo.yaml: plan meta, kind pack + overrides, compile defaults.

    @purpose  Everything plan-wide in one validated object; raw kind overrides
              stay unparsed here and resolve in kinds.resolve_kinds.
    """

    format: int = FORMAT_VERSION
    plan: str = ""
    description: str = ""
    pack: str | None = None
    kind_overrides: dict[str, Any] = Field(default_factory=dict)
    compile: CompileSettings = Field(default_factory=CompileSettings)


def default_title(node_id: str) -> str:
    """Humanize an id into a display title: last segment, dashes to spaces.

    @purpose  Titles are optional in frontmatter; every node still renders with one.
    """
    last = node_id.rsplit("/", 1)[-1].replace("-", " ").strip()
    return last[:1].upper() + last[1:]
