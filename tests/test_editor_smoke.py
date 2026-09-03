"""
@file        tests/test_editor_smoke.py
@purpose     The M5 tripwire, in a real browser: build a three-node plan
             entirely in the GUI (add via form, draw a needs edge between
             handles, edit a field, drag a node), braid it from the button, and
             then hold the files to the canonical forms — the whole loop or
             nothing. K31's own real-browser proof lives here too: a real CLI
             subprocess mutating the same plan while the editor is open must
             show exactly one attributed toast and pulse the right node, and
             an editor-driven gesture (this same session's own GUI add) must
             show none. K32's real-browser proof: adding a node through the
             GUI and pressing Ctrl+Z removes it from both the canvas and disk.
             Skips cleanly when Playwright's chromium is not installed.
@layer       tests
@tags        playwright, smoke, editor, e2e, events, attribution, undo
@related     frontend/src/App.tsx (the surface driven here),
             frontend/src/useAttribution.ts (the toast/pulse state under
             test), frontend/src/useUndoTrail.ts, frontend/src/useGraphKeyboard.ts
             (Ctrl+Z, under test), kumihimo/server/ops_api.py (where every
             gesture lands, inverse envelopes included), kumihimo/core/ops.py
             (the events.jsonl log a real `kumihimo add` subprocess writes to,
             actor "cli")
@design      PLAN.md §9 M5, roadmap item playwright-smoke; PLAN2.md §2.5
             Motion & attribution (K31) and Undo trail (K32)
"""

import contextlib
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from kumihimo import Plan

playwright_api = pytest.importorskip("playwright.sync_api")

PORT = 8731
URL = f"http://127.0.0.1:{PORT}"
STATIC = Path(__file__).resolve().parent.parent / "kumihimo" / "server" / "static"

pytestmark = pytest.mark.skipif(
    not (STATIC / "index.html").is_file(),
    reason="frontend not built (npm --prefix frontend run build)",
)


def kumihimo_argv(*args: str) -> list[str]:
    """The real `kumihimo` command line, console-script-first.

    @purpose  Shared by the `editor` fixture (launching the server) and the
              K31 test (a real CLI mutation while it's up): the console
              script direct, so signaling a `uv run` wrapper doesn't leave
              the actual process running (orphaned on Windows, TERM-shielded
              on Linux) — for a one-shot verb like `add` this mostly just
              keeps both call sites honest about which `kumihimo` runs.
    """
    venv = Path(__file__).resolve().parent.parent / ".venv"
    candidates = (venv / "Scripts" / "kumihimo.exe", venv / "bin" / "kumihimo")
    exe = next((str(c) for c in candidates if c.is_file()), None)
    return ([exe] if exe else ["uv", "run", "kumihimo"]) + list(args)


@pytest.fixture
def editor(tmp_path: Path) -> Iterator[Path]:
    """A live kumihimo edit server on an empty plan, torn down afterwards.

    @purpose  The smoke drives the real server and the real built frontend —
              TestClient hides too much for a tripwire.
    """
    root = tmp_path / "smoke"
    (root / "nodes").mkdir(parents=True)
    (root / "kumihimo.yaml").write_bytes(b"format: 1\nplan: Smoke\nkinds:\n  from: engineering\n")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            pytest.skip(f"port {PORT} busy")
    command = kumihimo_argv("edit", str(root), "--no-open", "--port", str(PORT))
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 40
        while time.time() < deadline:
            with contextlib.suppress(Exception):
                if httpx.get(f"{URL}/api/plan", timeout=1).status_code == 200:
                    break
            time.sleep(0.3)
        else:
            pytest.fail("editor server never came up")
        yield root
    finally:
        # Teardown must never fail a passed test: escalate TERM -> KILL.
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def drag(page: object, source_selector: str, target_selector: str) -> None:
    """Drag from one element's center to another's, in small steps.

    @purpose  React Flow's connect gesture needs real mouse movement, not a
              synthetic drop event.
    """
    source = page.locator(source_selector).bounding_box()  # type: ignore[attr-defined]
    target = page.locator(target_selector).bounding_box()  # type: ignore[attr-defined]
    assert source and target
    mouse = page.mouse  # type: ignore[attr-defined]
    mouse.move(source["x"] + source["width"] / 2, source["y"] + source["height"] / 2)
    mouse.down()
    mouse.move(target["x"] + target["width"] / 2, target["y"] + target["height"] / 2, steps=12)
    mouse.up()


def test_build_a_plan_in_the_gui_and_braid_it(editor: Path) -> None:
    # Only a missing browser is a skip; every other Playwright error is a real
    # failure and must fail (a first draft caught them all and laundered a bug
    # into a 37-second "skip").
    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")

            for node_id, title in (
                ("spec", "Write the spec"),
                ("build", "Build the thing"),
                ("verify", "Verify it works"),
            ):
                page.fill('input[placeholder="id-slug"]', node_id)
                page.fill('input[placeholder="title (optional)"]', title)
                page.get_by_role("button", name="Add", exact=True).click()
                page.wait_for_selector(f'.react-flow__node[data-id="{node_id}"]')

            # Draw needs edges by dragging handle to handle: build needs spec,
            # verify needs build (edge mode defaults to needs). After each op,
            # let the watcher echo and the elk re-layout settle before the next
            # gesture — the layout legitimately moves when edges appear.
            page.wait_for_timeout(700)
            page.locator(".react-flow__controls-fitview").click()
            page.wait_for_timeout(300)
            drag(
                page,
                '.react-flow__node[data-id="spec"] .react-flow__handle-right',
                '.react-flow__node[data-id="build"] .react-flow__handle-left',
            )
            page.wait_for_selector(
                'g.react-flow__edge[data-id="needs:spec->build"]', state="attached"
            )
            page.wait_for_timeout(700)
            page.locator(".react-flow__controls-fitview").click()
            page.wait_for_timeout(300)
            drag(
                page,
                '.react-flow__node[data-id="build"] .react-flow__handle-right',
                '.react-flow__node[data-id="verify"] .react-flow__handle-left',
            )
            page.wait_for_selector(
                'g.react-flow__edge[data-id="needs:build->verify"]', state="attached"
            )
            page.wait_for_timeout(700)

            # Edit a field through the form: build gets effort M.
            page.locator('.react-flow__node[data-id="build"] .kumi-node').click()
            page.wait_for_selector(".kumi-detail")
            page.select_option('.kumi-detail label:has-text("effort") select', "M")
            page.get_by_role("button", name="Save", exact=True).click()
            page.wait_for_timeout(400)

            # Drag a node body: position must land in view.yaml. Spec is the
            # leftmost node — the rightmost can sit under the minimap overlay,
            # which would swallow the mousedown.
            node_box = page.locator('.react-flow__node[data-id="spec"]').bounding_box()
            assert node_box
            page.mouse.move(node_box["x"] + 60, node_box["y"] + 10)
            page.mouse.down()
            page.mouse.move(node_box["x"] + 260, node_box["y"] + 140, steps=10)
            page.mouse.up()
            page.wait_for_timeout(400)

            # Braid from the button and read the prompt out of the modal.
            page.get_by_role("button", name="Braid", exact=True).click()
            page.wait_for_selector(".kumi-braid")
            braid_text = page.locator(".kumi-braid").inner_text()
        finally:
            browser.close()

    assert "# Braid: Smoke" in braid_text
    assert braid_text.index("Write the spec") < braid_text.index("Build the thing")
    assert braid_text.index("Build the thing") < braid_text.index("Verify it works")

    plan = Plan.load(editor)
    assert plan.nodes["build"].needs == ["spec"]
    assert plan.nodes["verify"].needs == ["build"]
    assert plan.nodes["build"].fields["effort"] == "M"
    build_file = (editor / "nodes" / "build.md").read_text(encoding="utf-8")
    assert build_file == "---\nkind: task\ntitle: Build the thing\nneeds: [spec]\neffort: M\n---\n"
    view = (editor / "view.yaml").read_text(encoding="utf-8")
    assert "spec: {x:" in view
    assert plan.check() == [
        finding for finding in plan.check() if finding.level == "warning"
    ]  # empty bodies warn; no errors


def test_cli_mutation_shows_one_toast_and_pulse_editor_self_op_shows_none(editor: Path) -> None:
    """K31's acceptance line, proven in a real browser: a CLI mutation to the
    open plan produces exactly one attributed toast plus a pulse on the
    right node; this same session's own GUI gesture produces neither."""
    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")

            # Editor self-op: add through the GUI, then give the watcher's
            # own echo of this exact change (well under a second, elsewhere
            # in this file) time to arrive — actor "editor" must raise
            # nothing at all, not even an "outside edit" toast.
            page.fill('input[placeholder="id-slug"]', "self")
            page.fill('input[placeholder="title (optional)"]', "Self op")
            page.get_by_role("button", name="Add", exact=True).click()
            page.wait_for_selector('.react-flow__node[data-id="self"]')
            page.wait_for_timeout(700)
            assert page.locator(".kumi-toast").count() == 0

            # A real CLI process, entirely outside this browser session.
            completed = subprocess.run(
                kumihimo_argv("add", str(editor), "via-cli", "--title", "Via CLI"),
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert completed.returncode == 0, completed.stderr

            page.wait_for_selector(".kumi-toast", timeout=5000)
            # Checked immediately on the same render pass the toast arrived
            # in, before the ~1s pulse animation can complete and remove its
            # own class (KumiNode.tsx's onAnimationEnd) — see useAttribution.
            toasts = page.locator(".kumi-toast")
            assert toasts.count() == 1
            toast_text = toasts.inner_text()
            assert toast_text.startswith("via CLI:")
            assert "Via CLI" in toast_text
            assert toast_text.endswith("added")
            assert page.locator('.react-flow__node[data-id="via-cli"].kumi-pulse').count() == 1
        finally:
            browser.close()

    assert Plan.load(editor).nodes["via-cli"].title == "Via CLI"


def test_gui_add_then_ctrl_z_undoes_it(editor: Path) -> None:
    """K32's acceptance line, proven in a real browser: adding a node through
    the GUI form, then pressing Ctrl+Z, removes it from both the canvas and
    disk — the undo trail's inverse posted through the same op door, not a
    second write path."""
    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")

            page.fill('input[placeholder="id-slug"]', "undoable")
            page.fill('input[placeholder="title (optional)"]', "Undo me")
            page.get_by_role("button", name="Add", exact=True).click()
            page.wait_for_selector('.react-flow__node[data-id="undoable"]')
            # The trail's own panel: one enabled entry for the add just made.
            page.wait_for_selector(".kumi-undo-entry:not([disabled])")

            page.keyboard.press("Control+z")
            page.wait_for_selector('.react-flow__node[data-id="undoable"]', state="detached")
        finally:
            browser.close()

    assert "undoable" not in Plan.load(editor).nodes
    assert not (editor / "nodes" / "undoable.md").exists()
