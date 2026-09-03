"""
@file        tools/demo_gif.py
@purpose     Regenerates the README's demo GIF: scaffolds a small themed
             scratch plan ("Ship the guard"), serves it with the real editor,
             drives headless chromium through a real `kumihimo set` CLI
             mutation (proving the attribution toast + node pulse) and a GUI
             field edit undone with Ctrl+Z (proving the undo trail), and
             assembles the captured frames into docs/assets/demo.gif with
             Pillow — shrinking colors, then frame count, then dimensions
             until the file is under the 4MB budget. Unlike
             tools/screenshots.py, this file imports kumihimo.core directly
             (add_node/link) to build the fixture in-process: the scratch
             plan needs an agents: mention, and `kumihimo link` has no CLI
             flag for one (only --needs/--in/--to — a real gap, not a
             workaround), so core.ops is the sanctioned door for that one
             edge. The one edit the GIF is actually ABOUT still goes through
             a real subprocess (kumihimo_argv), never ops directly — the
             whole point is an outside process touching the file.
@layer       tools
@tags        demo-gif, docs-assets, playwright, pillow, attribution, undo,
             screenshots
@related     tools/screenshots.py (the server-spawn + playwright pattern this
             mirrors), tests/test_editor_smoke.py (the same toast/pulse/undo
             gestures, proven there as assertions and here as a recording;
             also the venv-first `kumihimo` argv helper this copies),
             README.md (where the GIF is embedded above the fold),
             docs/index.md (the optional hero slot),
             kumihimo/core/ops.py (add_node/link — the fixture's only writer)
@design      PLAN2.md §2.5 Motion & attribution (K31), Undo trail (K32),
             queue item K39
"""

from __future__ import annotations

import argparse
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from kumihimo.core import ops
from kumihimo.core.plan import Plan

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
    from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
OUTPUT = ASSETS / "demo.gif"
PORT = 8748
VIEWPORT_WIDTH = 1200
VIEWPORT_HEIGHT = 750
FRAME_INTERVAL_MS = 320  # within the queue's ~250-400ms cadence
MAX_BYTES = 3_900_000  # "<4MB" with margin, whichever unit GitHub measures in
PLAN_NAME = "Ship the guard"

# The node the real CLI subprocess mutates (attribution toast + pulse) and
# the node the in-page form mutates then Ctrl+Z reverts — kept distinct so
# the two gestures never fight over the same card, and each demonstrates a
# clean before/after (middleware starts "doing" and finishes "done"; tests
# starts on the kind default "todo", visibly becomes "doing", then the
# undo's unset_fields restores that same default, not a fabricated value).
CLI_EDIT_NODE = "middleware"
GUI_EDIT_NODE = "tests"


@dataclass(frozen=True)
class DemoNode:
    """One scratch-plan node: id, kind, prose, and its needs/fields.

    @purpose  A plain data row so the plan's shape (build_plan) and its
              content (this table) stay visually separate.
    """

    id: str
    kind: str
    title: str
    body: str
    needs: tuple[str, ...] = ()
    # Every value in this demo's own table is a plain string (status/effort
    # choices, the agent's runtime/entry) — dict[str, str], not dict[str,
    # Any]: precise, and it sidesteps dict's value-type invariance biting
    # the NODES literal below (a real dict[str, Any] default would make
    # each entry's own literal dict need the exact same inferred type).
    fields: dict[str, str] = field(default_factory=dict)


NODES: tuple[DemoNode, ...] = (
    DemoNode(
        "spec",
        "task",
        "Write the rate-limit spec",
        "Define the limits, the response shape, and the Redis key scheme.",
        fields={"effort": "S"},
    ),
    DemoNode(
        "middleware",
        "task",
        "Build the middleware",
        "Wire the limiter into every authenticated route.",
        needs=("spec",),
        fields={"effort": "M", "status": "doing"},
    ),
    DemoNode(
        "tests",
        "task",
        "Add integration tests",
        "Cover the 429 path and the open-on-Redis-error fallback.",
        needs=("middleware",),
        fields={"effort": "M"},
    ),
    DemoNode(
        "ship",
        "task",
        "Ship to production",
        "Roll out behind a flag, watch the dashboards for a day.",
        needs=("tests",),
        fields={"effort": "S"},
    ),
    DemoNode(
        "reviewer",
        "agent",
        "Release reviewer",
        "Reviews the rollout plan before anything ships.",
        fields={"runtime": "claude-code", "entry": "/release-review"},
    ),
)
MENTION = ("ship", "reviewer")  # ship.agents += [reviewer]

# Fixed positions (NODE_WIDTH/NODE_HEIGHT are 210x66 — layout.ts): the
# "saved view.yaml" stability option the queue offers as an alternative to
# an auto-layout pass, chosen so the recording never depends on elk's lazily
# loaded chunk or its timing (K34).
POSITIONS: dict[str, tuple[int, int]] = {
    "spec": (40, 200),
    "middleware": (320, 200),
    "tests": (600, 200),
    "ship": (880, 200),
    "reviewer": (880, 380),
}


def build_plan(root: Path) -> None:
    """Scaffold the themed scratch plan directly on disk: manifest, five
    nodes (a needs chain plus one agent), the ship->reviewer mention, and a
    fixed view.yaml.

    @purpose  Everything the recording needs to look like a real, lived-in
              plan rather than a bare fixture; a hand-written manifest
              (mirroring tests/test_editor_smoke.py's fixture, not
              store.scaffold) so there's no generic "first-thread" starter
              node to clean up first.
    """
    (root / "nodes").mkdir(parents=True)
    manifest = f"format: 1\nplan: {PLAN_NAME}\nkinds:\n  from: engineering\n"
    (root / "kumihimo.yaml").write_bytes(manifest.encode("utf-8"))
    for node in NODES:
        ops.add_node(
            root,
            node.id,
            node.kind,
            title=node.title,
            body=node.body,
            fields=node.fields,
            needs=node.needs,
            actor="cli",
        )
    ops.link(root, MENTION[0], agents=MENTION[1], actor="cli")
    layout = "\n".join(f"  {node_id}: {{x: {x}, y: {y}}}" for node_id, (x, y) in POSITIONS.items())
    (root / "view.yaml").write_text(f"layout:\n{layout}\n", encoding="utf-8")
    errors = [finding for finding in Plan.load(root).check() if finding.level == "error"]
    if errors:
        raise RuntimeError(f"scratch plan fails its own check(): {errors}")


def _server_command(plan: Path, port: int) -> list[str]:
    """The editor launch command, venv script preferred over the uv wrapper.

    @purpose  Signaling a wrapper leaves the real server running; the direct
              script dies when told to — copied from tools/screenshots.py.
    """
    venv = ROOT / ".venv"
    candidates = (venv / "Scripts" / "kumihimo.exe", venv / "bin" / "kumihimo")
    exe = next((str(candidate) for candidate in candidates if candidate.is_file()), None)
    launcher = [exe] if exe else ["uv", "run", "kumihimo"]
    return [*launcher, "edit", str(plan), "--no-open", "--port", str(port)]


def _kumihimo_argv(*args: str) -> list[str]:
    """The real `kumihimo` command line, console-script-first.

    @purpose  What the recorded "outside edit" actually runs — same
              venv-first resolution as tests/test_editor_smoke.py's
              kumihimo_argv, so signaling a `uv run` wrapper never leaves an
              orphaned child behind.
    """
    venv = ROOT / ".venv"
    candidates = (venv / "Scripts" / "kumihimo.exe", venv / "bin" / "kumihimo")
    exe = next((str(candidate) for candidate in candidates if candidate.is_file()), None)
    return ([exe] if exe else ["uv", "run", "kumihimo"]) + list(args)


@contextlib.contextmanager
def serve(plan: Path, port: int) -> Iterator[str]:
    """A live editor server for one plan, killed on exit.

    @purpose  The recording drives the real server and the real built
              frontend, exactly what a user sees — copied from
              tools/screenshots.py.
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


def _capture(page: Page, frames: list[PILImage]) -> None:
    """Screenshot the viewport now and append it as an RGB frame.

    @purpose  One shared capture point so every phase feeds the same list in
              the same format (PNG bytes -> RGB, alpha dropped — a GIF frame
              has none anyway).
    """
    from PIL import Image

    png = page.screenshot(type="png", full_page=False)
    frames.append(Image.open(io.BytesIO(png)).convert("RGB"))


def _hold(page: Page, frames: list[PILImage], total_ms: int) -> None:
    """Capture frames at FRAME_INTERVAL_MS across a wait, so the GIF plays
    the pause itself instead of jump-cutting to the next gesture.

    @purpose  Pixel-identical adjacent frames cost nothing extra: Pillow's
              GIF writer merges them and sums their duration rather than
              dropping the held time (verified directly against this
              Pillow's own GifImagePlugin before relying on it here).
    """
    elapsed = 0
    while elapsed < total_ms:
        _capture(page, frames)
        page.wait_for_timeout(FRAME_INTERVAL_MS)
        elapsed += FRAME_INTERVAL_MS


def _status_text_is(page: Page, node_id: str, expected: str) -> None:
    """Wait until the given node's canvas card shows `expected` as its
    status text.

    @purpose  A precise, non-flaky settle point for phases 2-4: `status`
              carries a kind default ("todo"), so the span never
              disappears — only its text changes — a plain state="detached"
              wait would hang forever waiting for an element that's always
              there.
    """
    selector = f'.react-flow__node[data-id="{node_id}"] .kumi-status'
    page.wait_for_function(
        "([sel, text]) => document.querySelector(sel)?.textContent === text",
        arg=[selector, expected],
    )


def _phase_settle(page: Page, frames: list[PILImage]) -> None:
    """(1) Load, let the canvas settle, fit the view — the GIF's quiet open.

    @purpose  Shows the plan sitting still before anything happens, so the
              CLI edit two phases later reads as a change, not the intro.
    """
    page.wait_for_selector(".kumi-side h1")
    page.wait_for_selector(f'.react-flow__node[data-id="{MENTION[1]}"]')
    page.wait_for_timeout(400)
    page.locator(".react-flow__controls-fitview").click()
    page.wait_for_timeout(300)
    _hold(page, frames, 2200)


def _phase_cli_edit(page: Page, frames: list[PILImage], plan_root: Path, keyframes: Path) -> None:
    """(2) A real `kumihimo set` subprocess flips CLI_EDIT_NODE to done: the
    attribution toast and node pulse, held long enough to read.

    @purpose  K31's whole point, recorded rather than asserted: the editor
              never wrote this change, an outside process did, and the
              editor says so.
    """
    completed = subprocess.run(
        _kumihimo_argv("set", str(plan_root), CLI_EDIT_NODE, "--field", "status=done"),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"kumihimo set failed: {completed.stderr}")
    page.wait_for_selector(".kumi-toast", timeout=5000)
    _status_text_is(page, CLI_EDIT_NODE, "done")
    keyframes.joinpath("02-toast.png").write_bytes(page.screenshot(type="png"))
    _hold(page, frames, 3200)


def _phase_gui_edit(page: Page, frames: list[PILImage], keyframes: Path) -> None:
    """(3) Click GUI_EDIT_NODE, change status through the form select, Save.

    @purpose  The editor's own write path, in the same recording the CLI
              edit used — the contrast is the point (no toast/pulse here;
              K31 only fires for changes the editor didn't make itself).
    """
    page.locator(f'.react-flow__node[data-id="{GUI_EDIT_NODE}"] .kumi-node').click()
    page.wait_for_selector(".kumi-detail")
    page.locator(".kumi-detail").scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    _capture(page, frames)
    page.select_option('.kumi-detail label:has-text("status") select', "doing")
    page.wait_for_timeout(250)
    _capture(page, frames)
    page.get_by_role("button", name="Save", exact=True).click()
    _status_text_is(page, GUI_EDIT_NODE, "doing")
    keyframes.joinpath("03-gui-save.png").write_bytes(page.screenshot(type="png"))
    _hold(page, frames, 2200)


def _phase_undo(page: Page, frames: list[PILImage], keyframes: Path) -> None:
    """(4) Ctrl+Z: GUI_EDIT_NODE's status field is unset again, back to the
    kind default it started on — the undo trail's own inverse, posted
    through the same ops door as every other gesture.

    @purpose  K32's own proof, recorded: the sidebar's undo panel scrolled
              into frame so the trail (now two entries — the edit, and the
              undo-of-it) is legible alongside the reverted card.
    """
    page.locator(".kumi-undo").scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    _capture(page, frames)
    page.keyboard.press("Control+z")
    _status_text_is(page, GUI_EDIT_NODE, "todo")
    keyframes.joinpath("04-undo.png").write_bytes(page.screenshot(type="png"))
    _hold(page, frames, 2200)


def _shared_palette(frames: list[PILImage], colors: int) -> PILImage:
    """Build one adaptive palette from five frames spread across the whole
    recording, pasted side by side.

    @purpose  A single sampled frame risks a near-flat "settle" moment
              quantizing to a degenerate palette every other frame's colors
              then get crushed onto — verified directly: a solid-color
              sample frame collapsed a 5-color test sequence to visual
              duplicates. Spreading the sample across every phase means the
              toast border, the pulse ring, and every kind color actually
              earn a slot in the shared table.
    """
    from PIL import Image

    picks = sorted({round(i * (len(frames) - 1) / 4) for i in range(5)}) if len(frames) > 1 else [0]
    strip = Image.new("RGB", (frames[0].width * len(picks), frames[0].height))
    for offset, index in enumerate(picks):
        strip.paste(frames[index], (offset * frames[0].width, 0))
    return strip.quantize(colors=colors)


def assemble(frames: list[PILImage], frame_ms: int, path: Path) -> tuple[int, int, int, int, int]:
    """Quantize to a shared palette and write the animated GIF, shrinking
    (palette size, then frame count, then dimensions — the queue's own
    order) until it fits under MAX_BYTES.

    @purpose  The one place size is negotiated, so main() just reports
              whatever this actually wrote. Returns (bytes, width, height,
              the GIF's own real frame count, total loop milliseconds) —
              the real count, not len(quantized): Pillow's GIF writer
              silently merges pixel-identical adjacent frames into one and
              sums their duration (verified directly against this Pillow
              before relying on it), so a long static hold captured as many
              identical screenshots writes as far fewer actual frames.
              Total duration is unaffected by that merge either way — a
              scalar `duration` applies before merging — so it's plain
              `len(quantized) * step_ms`, computed at the same step_ms this
              call ends up writing with (colors shrink first; frame count
              only thins, doubling step_ms each time, after that's
              exhausted).
    @tags     gif, quantize, size-budget
    """
    from PIL import Image

    colors = 128
    working = frames
    step_ms = frame_ms
    scale = 1.0
    while True:
        scaled = (
            working
            if scale >= 1.0
            else [
                img.resize(
                    (max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                    Image.Resampling.LANCZOS,
                )
                for img in working
            ]
        )
        palette = _shared_palette(scaled, colors)
        quantized = [img.quantize(palette=palette, dither=Image.Dither.NONE) for img in scaled]
        buffer = io.BytesIO()
        quantized[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=quantized[1:],
            loop=0,
            duration=step_ms,
            optimize=True,
        )
        size = buffer.tell()
        if size <= MAX_BYTES:
            path.write_bytes(buffer.getvalue())
            buffer.seek(0)
            # n_frames is GifImagePlugin-specific, not on the base ImageFile
            # type mypy sees from Image.open() — getattr with a default
            # sidesteps that without a cast to a plugin-specific type.
            real_frames = int(getattr(Image.open(buffer), "n_frames", 1))
            total_ms = len(quantized) * step_ms
            return size, quantized[0].width, quantized[0].height, real_frames, total_ms
        if colors > 32:
            colors -= 32
        elif len(working) > 12:
            working = working[::2]
            step_ms *= 2
        elif scale > 0.5:
            scale -= 0.15
        else:
            raise RuntimeError(f"{path}: {size} bytes still exceeds {MAX_BYTES} after every shrink")


def record(plan_root: Path, keyframes: Path) -> tuple[list[PILImage], int]:
    """Serve the scratch plan and drive the four-phase choreography.

    @purpose  Isolates the playwright session from main()'s argument
              handling and the GIF assembly, so each stays readable.
    """
    from playwright.sync_api import sync_playwright

    frames: list[PILImage] = []
    with serve(plan_root, PORT) as url, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                device_scale_factor=1,
                color_scheme="light",
            )
            page.goto(url)
            _phase_settle(page, frames)
            _phase_cli_edit(page, frames, plan_root, keyframes)
            _phase_gui_edit(page, frames, keyframes)
            _phase_undo(page, frames, keyframes)
        finally:
            browser.close()
    return frames, FRAME_INTERVAL_MS


def main(argv: list[str] | None = None) -> int:
    """Build the scratch plan, record it, assemble the GIF, report the
    result.

    @purpose  What a maintainer runs after any change to the toast/pulse/
              undo surfaces, so the README's GIF never quietly goes stale.
    """
    parser = argparse.ArgumentParser(description="Regenerate docs/assets/demo.gif.")
    parser.add_argument(
        "--scratch",
        type=Path,
        default=None,
        help="Build the scratch plan here (left in place) instead of a throwaway temp dir.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the scratch plan and key frame PNGs (default temp dir only) for inspection.",
    )
    args = parser.parse_args(argv)

    owns_scratch = args.scratch is None and not args.keep
    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="kumihimo-demo-"))
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        plan_root = scratch / "ship-the-guard"
        if plan_root.exists():
            shutil.rmtree(plan_root)
        build_plan(plan_root)
        keyframes = scratch / "keyframes"
        keyframes.mkdir(exist_ok=True)

        frames, frame_ms = record(plan_root, keyframes)
        ASSETS.mkdir(parents=True, exist_ok=True)
        size, width, height, count, total_ms = assemble(frames, frame_ms, OUTPUT)
        print(
            f"{OUTPUT.relative_to(ROOT)}  {size / 1024:.0f} KB  {width}x{height}"
            f"  {count} frames  ~{total_ms / 1000:.1f}s loop"
        )
        if not owns_scratch:
            print(f"scratch plan kept at {scratch}")
    finally:
        if owns_scratch:
            shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
