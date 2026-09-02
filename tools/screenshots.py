"""
@file        tools/screenshots.py
@purpose     Regenerates the documentation screenshots: serves the shipped
             example plans with the real editor, drives headless chromium, and
             writes retina PNGs into docs/assets — so every UI change can
             re-shoot the docs in one command instead of leaving stale images.
@layer       tools
@tags        screenshots, docs-assets, playwright
@related     docs/index.md and README.md (where the images land),
             tests/test_editor_smoke.py (same server-spawning approach)
@design      PLAN.md §9 M6, PLAN2.md §6
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
BASE_PORT = 8742


def _server_command(plan: Path, port: int) -> list[str]:
    """The editor launch command, venv script preferred over the uv wrapper.

    @purpose  Signaling a wrapper leaves the real server running; the direct
              script dies when told to.
    """
    venv = ROOT / ".venv"
    candidates = (venv / "Scripts" / "kumihimo.exe", venv / "bin" / "kumihimo")
    exe = next((str(c) for c in candidates if c.is_file()), None)
    launcher = [exe] if exe else ["uv", "run", "kumihimo"]
    return [*launcher, "edit", str(plan), "--no-open", "--port", str(port)]


@contextlib.contextmanager
def serve(plan: Path, port: int) -> Iterator[str]:
    """A live editor server for one plan, killed on exit.

    @purpose  Screenshots come from the real server and the real built
              frontend, exactly what a user sees.
    """
    import httpx

    process = subprocess.Popen(
        _server_command(plan, port), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 40
        while time.time() < deadline:
            with contextlib.suppress(Exception):
                if httpx.get(f"{url}/api/plan", timeout=1).status_code == 200:
                    break
            time.sleep(0.3)
        else:
            raise RuntimeError(f"server for {plan} never came up")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def main() -> int:
    """Shoot every documented view and write the PNGs.

    @purpose  One command, current pixels: the editor with a node selected, the
              braid modal, and the dogfood roadmap canvas.
    """
    from playwright.sync_api import sync_playwright

    ASSETS.mkdir(parents=True, exist_ok=True)
    apiguard = ROOT / "examples" / "apiguard"
    roadmap = ROOT / "plans" / "roadmap"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)

        with serve(apiguard, BASE_PORT) as url:
            page.goto(url)
            page.wait_for_selector(".kumi-side h1")
            page.wait_for_timeout(1500)
            page.locator(".react-flow__controls-fitview").click()
            page.wait_for_timeout(400)
            page.locator('.react-flow__node[data-id="rate-limit-core"] .kumi-node').click()
            page.wait_for_selector(".kumi-detail")
            page.wait_for_timeout(400)
            page.screenshot(path=str(ASSETS / "canvas-editor.png"))
            page.get_by_role("button", name="Braid", exact=True).click()
            page.wait_for_selector(".kumi-braid")
            page.wait_for_timeout(300)
            page.screenshot(path=str(ASSETS / "braid-modal.png"))

        with serve(roadmap, BASE_PORT + 1) as url:
            page.goto(url)
            page.wait_for_selector(".kumi-side h1")
            page.wait_for_timeout(1800)
            page.locator(".react-flow__controls-fitview").click()
            page.wait_for_timeout(400)
            page.screenshot(path=str(ASSETS / "canvas-roadmap.png"))
            # The Status lens (key 2): ready frontier glowing, done dimmed —
            # M8's face for the docs.
            page.keyboard.press("2")
            page.wait_for_timeout(500)
            page.screenshot(path=str(ASSETS / "lens-status.png"))
            # The Crew lens (key 5): agent hues, unassigned outlines, trains
            # edges bold — M9's face, shot on the crewed roadmap itself.
            page.keyboard.press("5")
            page.wait_for_timeout(500)
            page.screenshot(path=str(ASSETS / "lens-crew.png"))
            page.keyboard.press("1")

        browser.close()
    for shot in sorted(ASSETS.glob("*.png")):
        print(f"{shot.relative_to(ROOT)}  {shot.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
