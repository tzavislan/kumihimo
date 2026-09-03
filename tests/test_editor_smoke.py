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
             K33's own proof lives in the braid section of the main flow:
             Rendered is the modal's default (a real <h1>), Raw still carries
             the exact compiled text, the Diagram toggle folds/unfolds the one
             ```mermaid fence in both views, and Copy/Download both carry the
             untouched braid — Download's bytes sha256-match a fresh
             GET /api/braid, proving no re-serialization happened anywhere
             between the API and the saved file. Skips cleanly when
             Playwright's chromium is not installed. K34's own proof is a
             separate, standalone test (its own tiny positioned plan and
             server): a network-log capture proving a fully-positioned cold
             load fetches no elk chunk at all, and that clicking Auto-layout
             fetches it exactly once right after — the main flow above
             already exercises the lazy elk path for free (every GUI
             add_node on the empty starting plan is itself a gap elk fills),
             so that half needed no new waits, only the standalone test for
             the "no fetch when nothing's missing" half it can't reach.
@layer       tests
@tags        playwright, smoke, editor, e2e, events, attribution, undo,
             braid-preview, elk, lazy-load, network-log
@related     frontend/src/App.tsx (the surface driven here),
             frontend/src/BraidModal.tsx (the Rendered/Raw/Diagram/Download
             surface under test, K33), frontend/src/braidPreview.ts (the fold
             transform and lazy `marked` render this exercises indirectly),
             frontend/src/layout.ts (elkPositions' dynamic import and
             hasLayoutGaps, both under test, K34),
             frontend/src/useAttribution.ts (the toast/pulse state under
             test), frontend/src/useUndoTrail.ts, frontend/src/useGraphKeyboard.ts
             (Ctrl+Z, under test), kumihimo/server/ops_api.py (where every
             gesture lands, inverse envelopes included), kumihimo/core/ops.py
             (the events.jsonl log a real `kumihimo add` subprocess writes to,
             actor "cli"), kumihimo/server/app.py (GET /api/braid — the bytes
             Download must sha256-match)
@design      PLAN.md §9 M5, roadmap item playwright-smoke; PLAN2.md §2.5
             Motion & attribution (K31) and Undo trail (K32); PLAN2.md §4 M10
             styled braid preview (K33), queue item K34 (elk lazy-load)
"""

import contextlib
import hashlib
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

            # Braid from the button. Rendered is the modal's default view
            # (K33) — its own <h1> proves "# Braid: Smoke" actually rendered
            # as a heading, not just arrived as text in a <pre>. The Smoke
            # plan has needs edges but no membership, so diagram.py's
            # mermaid() still emits a real (small) "Plan shape" fence —
            # folded by default, so neither the heading's own diagram-hidden
            # placeholder nor the rendered pane should show "graph LR" yet.
            page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=URL)
            page.get_by_role("button", name="Braid", exact=True).click()
            page.wait_for_selector(".kumi-braid-rendered h1")
            rendered_h1 = page.locator(".kumi-braid-rendered h1").inner_text()
            rendered_folded = page.locator(".kumi-braid-rendered").inner_text()

            # Raw carries the exact compiled text — same fold, same text,
            # just <pre> instead of marked's HTML (K33: both views share one
            # fold transform over the one ```mermaid fence).
            page.get_by_role("tab", name="Raw", exact=True).click()
            page.wait_for_selector(".kumi-braid")
            braid_text = page.locator(".kumi-braid").inner_text()

            # Copy and Download, both while STILL folded: the point of this
            # ordering is that if either wired itself to the folded display
            # copy instead of the untouched prop, the diagram would come back
            # as the "(...hidden...)" placeholder instead of real "graph LR"
            # source — folding is a reading aid, never a data loss risk for
            # what gets copied or downloaded (K33's own invariant).
            page.get_by_role("button", name="Copy", exact=True).click()
            clipboard_text = page.evaluate("navigator.clipboard.readText()")
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Download", exact=True).click()
            download = download_info.value
            download_filename = download.suggested_filename
            downloaded_bytes = Path(download.path()).read_bytes()

            # The Diagram toggle unfolds the fence in both views alike;
            # get_by_title rather than get_by_role — this button is the one
            # control in the modal whose title is deliberately more precise
            # than its short, state-flipping visible label.
            page.get_by_title(
                "Mermaid itself is never rendered — this only shows or hides the fenced source"
            ).click()
            page.wait_for_function(
                "document.querySelector('.kumi-braid').innerText.includes('graph LR')"
            )
            raw_unfolded = page.locator(".kumi-braid").inner_text()
        finally:
            browser.close()

    api_bytes = httpx.get(f"{URL}/api/braid").content
    assert rendered_h1 == "Braid: Smoke"
    assert "diagram hidden" in rendered_folded
    assert "graph LR" not in rendered_folded
    assert "# Braid: Smoke" in braid_text
    assert braid_text.index("Write the spec") < braid_text.index("Build the thing")
    assert braid_text.index("Build the thing") < braid_text.index("Verify it works")
    assert "diagram hidden" in braid_text
    assert "graph LR" not in braid_text
    # Windows' system clipboard normalizes plain text to CRLF regardless of
    # what any web app writes (a browser/OS convention outside this app's
    # control) — Copy is checked for CONTENT fidelity accordingly. Download's
    # Blob path never touches the OS clipboard at all, so it alone is held to
    # the acceptance line's literal byte-for-byte bar, below.
    assert clipboard_text.replace("\r\n", "\n") == api_bytes.decode("utf-8")
    assert "graph LR" in clipboard_text  # the real diagram, not the fold placeholder
    assert download_filename == "smoke.braid.md"
    assert hashlib.sha256(downloaded_bytes).hexdigest() == hashlib.sha256(api_bytes).hexdigest()
    assert "graph LR" in raw_unfolded  # the Diagram toggle unfolded it back

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


# Checker-flagged gap, fixed same day the checker found it live: the html-
# escape override alone left marked's default link/image renderers doing no
# scheme filtering at all — a node body's [x](javascript:alert(1)) or the
# CommonMark autolink <javascript:alert(1)> rendered as a real, clickable
# <a href="javascript:alert(1)">, confirmed by clicking one in the running
# app. braidPreview.ts's link/image renderer overrides fix this; this test
# is the checker's own two vectors plus data: (link and image), a
# denied-scheme link's nested formatting surviving as inert text, ordinary
# http(s)/relative/fragment links still producing real anchors, and a wider
# raw-HTML-escape regression sweep (script/event-handler-attribute/comment/
# entity/code vectors) — all read straight out of the live rendered DOM, not
# just string-matched off the HTML source, so a payload that parses into
# some OTHER live element this test didn't think to name would still be
# caught by the anchor/img inventory or the innerHTML assertions below.
def test_braid_preview_escapes_html_and_filters_link_schemes(editor: Path) -> None:
    body = "\n\n".join(
        [
            "Vector 1 script tag: <script>alert(1)</script>",
            'Vector 2 img onerror: <img src=x onerror="alert(2)">',
            'Vector 3 svg onload: <svg onload="alert(3)">',
            'Vector 4 iframe javascript src: <iframe src="javascript:alert(4)"></iframe>',
            'Vector 5 anchor onclick raw html: <a href="#" onclick="alert(5)">raw</a>',
            "Vector 6 html comment: <!-- <script>alert(6)</script> -->",
            "Vector 7 already-escaped entity: &lt;script&gt;",
            "Vector 8 inline code literal: `<script>alert(8)</script>`",
            "Checker vector: reference-style javascript link: [click me](javascript:alert(9))",
            "Checker vector: CommonMark autolink: <javascript:alert(10)>",
            "data link: [data click](data:text/html,<script>alert(11)</script>)",
            "data image below:",
            "![data image](data:image/png;base64,AAAA)",
            "Bold inside a denied link: [**bold click**](javascript:alert(12))",
            "Legit https link: [anthropic](https://www.anthropic.com)",
            "Legit relative link: [readme](./README.md)",
            "Legit fragment link: [section](#section)",
            "Legit https image below:",
            "![legit image](https://example.com/pic.png)",
        ]
    )
    body += "\n\n```js\nfenced code block literal: <script>alert(13)</script>\n```\n"
    completed = subprocess.run(
        kumihimo_argv("add", str(editor), "payload", "--title", "Payload node", "--body", body),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr

    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")
            page.get_by_role("button", name="Braid", exact=True).click()
            page.wait_for_selector(".kumi-braid-rendered h1")
            rendered = page.eval_on_selector(
                ".kumi-braid-rendered",
                "(el) => ({"
                " html: el.innerHTML,"
                " anchors: [...el.querySelectorAll('a')].map(a => a.getAttribute('href')),"
                " imgs: [...el.querySelectorAll('img')].map(i => i.getAttribute('src')),"
                " strongCount: el.querySelectorAll('strong').length,"
                " scriptCount: el.querySelectorAll('script').length,"
                " iframeCount: el.querySelectorAll('iframe').length,"
                " svgCount: el.querySelectorAll('svg').length,"
                # Real DOM attribute presence, not a string search over the
                # HTML source — the point is "would the browser ever
                # actually run this," which only a live element with the
                # attribute really set can answer. A properly-escaped
                # payload leaves the WORD 'onerror=' sitting in plain text
                # (that's expected and fine); this only fires on a genuine
                # attribute.
                " dangerousAttrElements: el.querySelectorAll("
                "   '[onclick],[onerror],[onload],[onmouseover],'"
                ' + \'[href^="javascript:" i],[src^="javascript:" i]\''
                " ).length,"
                "})",
            )

            # Raw view too: React's own text interpolation makes it safe by
            # construction, but confirm no vector reaches it as a live
            # element either, and the fold-affordance path stays untouched.
            page.get_by_role("tab", name="Raw", exact=True).click()
            page.wait_for_selector(".kumi-braid")
            raw_has_anchor = page.eval_on_selector(".kumi-braid", "(el) => !!el.querySelector('a')")
            raw_has_img = page.eval_on_selector(".kumi-braid", "(el) => !!el.querySelector('img')")
            raw_has_script = page.eval_on_selector(
                ".kumi-braid", "(el) => !!el.querySelector('script')"
            )
        finally:
            browser.close()

    html = rendered["html"]
    anchors = rendered["anchors"]
    imgs = rendered["imgs"]

    # --- the checker's two demonstrated vectors, plus data: for both link
    # and image: no live/navigable element at all, not merely a filtered one.
    assert not any(href.startswith(("javascript:", "data:", "vbscript:")) for href in anchors)
    assert not any(src.startswith("data:") for src in imgs)  # data: image denied, not just this one
    assert "click me" in html  # link text still visible, just not wrapped in <a>
    assert "javascript:alert(10)" in html  # the autolink's own text (== its href) still visible

    # --- ordinary links/images are unaffected by the allow-list.
    assert anchors == ["https://www.anthropic.com", "./README.md", "#section"]
    assert imgs == ["https://example.com/pic.png"]  # data: image denied; this https one wasn't

    # --- nested formatting inside a denied link still renders (K33's own
    # "hostile input degrades to visible text, never to a live element" —
    # not to nothing).
    assert rendered["strongCount"] >= 1

    # --- raw-HTML escape regression: every vector above stays inert text.
    # Real DOM checks (element/attribute counts), not string-in-html checks
    # for the attribute names — "onerror=" legitimately appears as plain
    # visible TEXT once escaped (only the surrounding <> and quotes change),
    # so a substring search for it would false-positive on correctly-escaped
    # output; only a live element actually carrying the attribute matters.
    assert rendered["scriptCount"] == 0
    assert rendered["iframeCount"] == 0
    assert rendered["svgCount"] == 0
    assert rendered["dangerousAttrElements"] == 0
    assert "<script>" not in html
    assert "<iframe" not in html
    assert "<svg" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html  # vector 1, escaped
    assert "&lt;script&gt;" in html  # vector 7, single-decoded (not &amp;lt;)
    assert "&amp;lt;" not in html  # would mean vector 7 got double-escaped
    assert "<code>&lt;script&gt;alert(8)&lt;/script&gt;</code>" in html  # vector 8
    assert '<pre><code class="language-js">' in html  # fenced block still a real code block
    assert "&lt;script&gt;alert(13)&lt;/script&gt;" in html  # ...with its content literal

    # --- Raw view: no vector reaches it as a live element either.
    assert raw_has_anchor is False
    assert raw_has_img is False
    assert raw_has_script is False


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


def test_cold_load_with_full_positions_skips_elk_until_layout_runs(tmp_path: Path) -> None:
    """K34's own acceptance line, network-log-proven: layout.ts's elkPositions
    is a dynamic import now, and App.tsx's hasLayoutGaps skips calling it
    entirely when view.yaml already positions every node — so a
    fully-positioned plan's cold load must fetch NO elk chunk at all.
    Clicking Auto-layout right after must fetch it exactly once, proving the
    absence above is the skip actually working, not elk being broken and
    never loading at all. Its own tiny plan and server, deliberately not the
    shared `editor` fixture: that one starts empty, where every GUI add_node
    is itself a gap and would fetch elk immediately — the opposite of what
    this test needs to set up."""
    root = tmp_path / "positioned"
    (root / "nodes").mkdir(parents=True)
    (root / "kumihimo.yaml").write_bytes(
        b"format: 1\nplan: Positioned\nkinds:\n  from: engineering\n"
    )
    for node_id in ("alpha", "beta"):
        (root / "nodes" / f"{node_id}.md").write_text(
            f"---\nkind: task\ntitle: {node_id.title()}\n---\nBody.\n", encoding="utf-8"
        )
    (root / "view.yaml").write_text(
        "layout:\n  alpha: {x: 40, y: 40}\n  beta: {x: 320, y: 40}\n", encoding="utf-8"
    )
    port = PORT + 1
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            pytest.skip(f"port {port} busy")
    command = kumihimo_argv("edit", str(root), "--no-open", "--port", str(port))
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f"http://127.0.0.1:{port}"
        deadline = time.time() + 40
        while time.time() < deadline:
            with contextlib.suppress(Exception):
                if httpx.get(f"{url}/api/plan", timeout=1).status_code == 200:
                    break
            time.sleep(0.3)
        else:
            pytest.fail("editor server never came up")

        with playwright_api.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except playwright_api.Error as err:
                pytest.skip(f"chromium not launchable: {err}")
            try:
                page = browser.new_page(viewport={"width": 1400, "height": 900})
                requests: list[str] = []
                page.on("request", lambda request: requests.append(request.url))
                page.goto(url)
                page.wait_for_selector('.react-flow__node[data-id="beta"]')
                page.wait_for_timeout(500)
                assert not any("elk" in r for r in requests), (
                    f"elk fetched on cold load: {requests}"
                )

                page.get_by_role("button", name="Auto-layout", exact=True).click()
                page.wait_for_timeout(800)
                assert any("elk" in r for r in requests), (
                    f"Auto-layout never fetched elk: {requests}"
                )
            finally:
                browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def test_chip_add_disables_during_flight_then_second_add_lands_clean(editor: Path) -> None:
    """K40's acceptance line, proven in a real browser: two fast chip adds on
    the same node must not 409 each other. ChipEditor.tsx's add input
    disables the instant a chip op posts (checked immediately below, before
    any wait, so this fails if the guard were only a post-hoc cleanup) and
    re-enables only once that op's response — success or failure alike —
    echoes back; a script that waits for the re-enable before its second
    click therefore lands both edges with zero conflict notices, closing the
    race the audit found (the second add firing while the first still held
    the pre-echo digest, 409ing)."""
    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")

            for node_id, title in (("alpha", "Alpha"), ("bravo", "Bravo"), ("charlie", "Charlie")):
                page.fill('input[placeholder="id-slug"]', node_id)
                page.fill('input[placeholder="title (optional)"]', title)
                page.get_by_role("button", name="Add", exact=True).click()
                page.wait_for_selector(f'.react-flow__node[data-id="{node_id}"]')

            page.locator('.react-flow__node[data-id="alpha"] .kumi-node').click()
            page.wait_for_selector(".kumi-detail")

            needs_input = page.locator('input[aria-label="Add needs"]')
            needs_add = page.locator('button[aria-label="Add needs"]')

            needs_input.fill("bravo")
            needs_add.click()
            # Disabled the instant the gesture posts (K40) — not a later,
            # eventual state; the row's own input carries no other reason to
            # ever be disabled, so this alone proves the guard fired.
            assert needs_input.is_disabled()

            # Re-enabled once the response lands; only then does the script
            # fire the second add — the exact "wait for enable, then add"
            # proof the acceptance line asks for.
            page.wait_for_selector('input[aria-label="Add needs"]:not([disabled])', timeout=5000)
            assert page.locator(".kumi-notice").count() == 0  # no conflict notice from the first

            needs_input.fill("charlie")
            needs_add.click()
            assert needs_input.is_disabled()
            page.wait_for_selector('input[aria-label="Add needs"]:not([disabled])', timeout=5000)

            page.wait_for_selector('.kumi-chip-pill:has-text("Bravo")')
            page.wait_for_selector('.kumi-chip-pill:has-text("Charlie")')
            assert page.locator(".kumi-notice").count() == 0  # zero conflict notices throughout
        finally:
            browser.close()

    assert Plan.load(editor).nodes["alpha"].needs == ["bravo", "charlie"]


def test_crew_lens_status_gate_form_banner_and_esc_clears_selection(editor: Path) -> None:
    """Three of K41's four audit fixes, proven in a real browser.
    (1) Crew lens: a task with no agents outlines as unassigned only while
    its effective status isn't done — the same task loses the outline the
    instant its status flips to done, agents still empty. (3) The node form
    banners which node it's editing at the top. (4) With nothing else active
    (no palette, no braid modal, no focus, no trace), Esc clears the current
    selection."""
    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")

            page.fill('input[placeholder="id-slug"]', "untitled-task")
            page.get_by_role("button", name="Add", exact=True).click()
            page.wait_for_selector('.react-flow__node[data-id="untitled-task"]')

            # (3) Banner, given no title: store.py's own default_title already
            # humanizes an empty title from the id before this form ever sees
            # it ("untitled-task" -> "Untitled task", core/model.py), so this
            # proves the banner reads live off `node.title`/`node.id`, not
            # NodeForm's OWN `|| node.id` fallback specifically — nothing in
            # the normal load path ever hands it a genuinely blank title to
            # exercise that branch on (store.py:238's own default-at-parse
            # guarantee), so that fallback stays defense-in-depth, unproven
            # here on purpose rather than faked via a hand-written file.
            page.locator('.react-flow__node[data-id="untitled-task"] .kumi-node').click()
            page.wait_for_selector(".kumi-detail")
            assert (
                page.locator(".kumi-detail-meta").inner_text()
                == "editing Untitled task · untitled-task"
            )

            page.fill('.kumi-detail label:has-text("Title") input', "Named now")
            page.get_by_role("button", name="Save", exact=True).click()
            page.wait_for_timeout(400)
            assert (
                page.locator(".kumi-detail-meta").inner_text()
                == "editing Named now · untitled-task"
            )

            # (1) Crew lens: no agents, status "todo" (the field's own
            # default) -> outlined unassigned.
            page.get_by_role("tab", name="Crew", exact=True).click()
            page.wait_for_selector(
                '.react-flow__node[data-id="untitled-task"].kumi-crew-unassigned'
            )

            # Flip status to done, no agents added — the outline must drop.
            page.select_option('.kumi-detail label:has-text("status") select', "done")
            page.get_by_role("button", name="Save", exact=True).click()
            page.wait_for_timeout(600)
            assert (
                page.locator(
                    '.react-flow__node[data-id="untitled-task"].kumi-crew-unassigned'
                ).count()
                == 0
            )

            # (4) Esc with nothing else active (no palette, no braid modal,
            # no focus, no trace) clears the selection: the sidebar form
            # closes. Focus is on the Save button just clicked, not a form
            # field, so this Esc isn't swallowed by the form-field guard.
            page.keyboard.press("Escape")
            page.wait_for_selector(".kumi-detail", state="detached")
        finally:
            browser.close()

    plan = Plan.load(editor)
    assert plan.nodes["untitled-task"].title == "Named now"
    assert plan.nodes["untitled-task"].fields["status"] == "done"


def test_braid_preview_decodes_colon_entities_before_scheme_check(editor: Path) -> None:
    """K43.1's acceptance line: an HTML colon-character-reference hiding the
    scheme separator — decimal `&#58;`, or hex `&#x3a;`/`&#x3A;` — must not
    slip a javascript: link past braidPreview.ts's urlScheme allow-list the
    way it did before the checker's v13 finding. Decode once, then classify:
    the exact same denied-scheme-degrades-to-plain-text result the plain
    `javascript:` vectors already get in the main XSS sweep
    (test_braid_preview_escapes_html_and_filters_link_schemes above)."""
    body = "\n\n".join(
        [
            "Checker vector v13: decimal entity colon: "
            "[entity colon click](javascript&#58;alert(1))",
            "Checker vector v13: hex entity colon lowercase: "
            "[hex colon click lower](javascript&#x3a;alert(1))",
            "Checker vector v13: hex entity colon uppercase: "
            "[hex colon click upper](javascript&#x3A;alert(1))",
            "Legit https link unaffected: [anthropic](https://www.anthropic.com)",
        ]
    )
    completed = subprocess.run(
        kumihimo_argv(
            "add", str(editor), "entity-payload", "--title", "Entity payload", "--body", body
        ),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr

    with playwright_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except playwright_api.Error as err:
            pytest.skip(f"chromium not launchable: {err}")
        try:
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(URL)
            page.wait_for_selector(".kumi-side h1")
            page.get_by_role("button", name="Braid", exact=True).click()
            page.wait_for_selector(".kumi-braid-rendered h1")
            rendered = page.eval_on_selector(
                ".kumi-braid-rendered",
                "(el) => ({"
                " html: el.innerHTML,"
                " anchors: [...el.querySelectorAll('a')].map(a => a.getAttribute('href')),"
                "})",
            )
        finally:
            browser.close()

    html = rendered["html"]
    anchors = rendered["anchors"]
    # Not one entity-obscured vector produced a live anchor — only the
    # ordinary https link did.
    assert anchors == ["https://www.anthropic.com"]
    assert "entity colon click" in html  # label visible, no <a> wrapper
    assert "hex colon click lower" in html
    assert "hex colon click upper" in html
