"""
@file        kumihimo/core/plan.py
@purpose     The Plan facade — the object users import: load a directory, look at
             nodes and kinds, check it, save what changed. Orchestrates store and
             kinds; grows check() wiring at K4 and braid() at M2.
@layer       core
@tags        plan, facade, public-api
@related     kumihimo/core/store.py (does the IO),
             kumihimo/core/kinds.py (resolves the kind system),
             kumihimo/__init__.py (re-exports Plan)
@design      PLAN.md §7.2
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from kumihimo.core import kinds as kinds_module
from kumihimo.core import store, validate
from kumihimo.core.errors import KumihimoError
from kumihimo.core.model import Finding, KindDef, Manifest, Node
from kumihimo.core.store import LoadedPlan, NodeRecord

_BRAIDER: Callable[..., str] | None = None


def register_braider(braider: Callable[..., str]) -> None:
    """Install the compile layer's braid function behind Plan.braid.

    @purpose  Dependency inversion for invariant 3: core never imports compile;
              compile registers itself here when it loads (kumihimo/__init__
              guarantees that for library users).
    """
    global _BRAIDER
    _BRAIDER = braider


class Plan:
    """A loaded plan: manifest, resolved kinds, node records, findings.

    @purpose  The one aggregate every client holds; a snapshot of disk that knows
              how to write its own changes back.
    @tags     plan, aggregate
    """

    def __init__(
        self,
        loaded: LoadedPlan,
        kinds: dict[str, KindDef],
        kind_findings: list[Finding],
    ) -> None:
        """Wire a loaded plan to its resolved kind system.

        @purpose  Constructor for Plan.load; direct use is for tests.
        """
        self._loaded = loaded
        self.kinds = kinds
        self.load_findings: list[Finding] = [*loaded.findings, *kind_findings]

    @classmethod
    def load(cls, path: str | Path) -> Plan:
        """Load the plan directory at path.

        @purpose  The library's front door; content problems become findings on
                  the returned Plan, only "not a plan" raises.
        """
        loaded = store.load(Path(path))
        kinds, kind_findings = kinds_module.resolve_kinds(
            loaded.manifest.pack, loaded.manifest.kind_overrides
        )
        return cls(loaded, kinds, kind_findings)

    @property
    def root(self) -> Path:
        """The plan directory.

        @purpose  Clients need it for messages and relative paths.
        """
        return self._loaded.root

    @property
    def manifest(self) -> Manifest:
        """The parsed manifest.

        @purpose  Compile settings and plan meta for clients and the braid.
        """
        return self._loaded.manifest

    @property
    def records(self) -> dict[str, NodeRecord]:
        """Node records by id, in sorted-file order.

        @purpose  The mutable layer ops work on; most readers want .nodes instead.
        """
        return self._loaded.records

    @property
    def nodes(self) -> dict[str, Node]:
        """Nodes by id.

        @purpose  The read-only view almost every consumer wants.
        """
        return {node_id: record.node for node_id, record in self._loaded.records.items()}

    def node(self, node_id: str) -> Node:
        """One node by id, or a clean error naming it.

        @purpose  KeyError with context, as a KumihimoError clients can print.
        """
        record = self._loaded.records.get(node_id)
        if record is None:
            raise KumihimoError(f"no node '{node_id}' in {self.root.name}")
        return record.node

    def check(self) -> list[Finding]:
        """Everything wrong or suspicious about the plan, errors first.

        @purpose  Load findings plus every rule in validate.py, in deterministic
                  order — the one validation answer every surface renders.
        """
        return validate.check(self)

    def braid(self, **kwargs: Any) -> str:
        """Compile this plan (or a slice) into one prompt; see compile.braid.

        @purpose  The public sugar over the pipeline — accepts strategy, where,
                  from_, until, in_, diagram, dry; returns the woven text.
        """
        if _BRAIDER is None:
            raise KumihimoError("compile layer not loaded; import kumihimo, not kumihimo.core")
        return _BRAIDER(self, **kwargs)

    def save(self) -> list[str]:
        """Write every dirty record; return the rel paths written.

        @purpose  Fidelity contract surface: an untouched plan saves to an empty
                  list and zero writes.
        """
        written: list[str] = []
        for record in self._loaded.records.values():
            if store.save_record(record):
                written.append(record.path.relative_to(self.root).as_posix())
        return written
