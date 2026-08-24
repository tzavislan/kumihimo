"""
@file        hatch_build.py
@purpose     Wheel build hook: force-include the built frontend
             (kumihimo/server/static) when it exists. The directory is
             gitignored — Vite writes it — and hatchling's `artifacts` config
             proved unreliable for it under the packages shorthand, so the hook
             includes it explicitly and only when present, keeping builds
             working on machines that never ran npm.
@layer       tools
@tags        packaging, wheel, frontend, build-hook
@related     frontend/vite.config.ts (writes the directory this ships),
             kumihimo/server/app.py (serves it, with an honest fallback)
@design      PLAN.md §9 M4, roadmap item wheel-assets
"""

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):  # type: ignore[type-arg]
    """Adds the built canvas to wheels that have one.

    @purpose  Ship static/ in release wheels without making Node a build
              requirement for anyone else.
    """

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Register the force-include when the frontend build output exists.

        @purpose  Presence-conditional: no static/, no entry, no error.
        """
        static = Path(self.root) / "kumihimo" / "server" / "static"
        if (static / "index.html").is_file():
            build_data["force_include"][str(static)] = "kumihimo/server/static"
