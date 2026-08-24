"""
@file        tests/conftest.py
@purpose     Shared fixtures: a factory that lays a plan directory on disk from a
             dict of node files, so every test builds real plans the way users
             have them — as files.
@layer       tests
@tags        fixtures, plan-factory
@related     kumihimo/core/store.py (what the factory's output exercises)
@design      PLAN.md §7.3
"""

from collections.abc import Callable
from pathlib import Path

import pytest

DEFAULT_MANIFEST = "format: 1\nplan: Fixture\nkinds:\n  from: engineering\n"

PlanFactory = Callable[..., Path]


@pytest.fixture
def plan_dir(tmp_path: Path) -> PlanFactory:
    """Factory fixture: plan_dir(files, manifest=...) -> plan root path.

    @purpose  One canonical way to lay fixture plans on disk, bytes-exact.
    """

    def make(files: dict[str, str], manifest: str = DEFAULT_MANIFEST) -> Path:
        root = tmp_path / "plan"
        (root / "nodes").mkdir(parents=True)
        (root / "kumihimo.yaml").write_bytes(manifest.encode("utf-8"))
        for name, text in files.items():
            target = root / "nodes" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
        return root

    return make
