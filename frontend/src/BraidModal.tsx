/**
 * @file        frontend/src/BraidModal.tsx
 * @purpose     The braid preview (K33): App.tsx's Braid button/palette command
 *              still just fetch the text and hand it here unmounted-or-not —
 *              this owns everything about SHOWING it. A Rendered/Raw switch
 *              (Rendered default — braidPreview.ts's marked, lazy-imported on
 *              first render so its chunk never ships in the initial bundle),
 *              a Diagram fold for the one ```mermaid "Plan shape" fence
 *              (mermaid itself is never rendered — out of budget against
 *              K34, PLAN2.md §4 M10), Copy (unchanged), and Download (a
 *              Blob built straight from the untouched `text` prop — never
 *              the folded/rendered display copy, so the file on disk always
 *              matches the braid API byte-for-byte). Always mounted by
 *              App.tsx (same "renders nothing while its prop says closed"
 *              shape as Palette.tsx) rather than conditionally, on purpose:
 *              plain useState for the view/fold choices then survives a
 *              close-and-reopen within the session for free, no localStorage
 *              and no extra plumbing needed to "remember" anything.
 * @layer       frontend
 * @tags        braid, modal, markdown, marked, lazy-load, download
 * @related     frontend/src/App.tsx (owns braidText state, mounts this
 *              unconditionally, fetches via api.ts's fetchBraid),
 *              frontend/src/braidPreview.ts (fold/render/slug — the only
 *              other file that knows about `marked`),
 *              frontend/src/styles.css (.kumi-braid-* rules, both themes),
 *              kumihimo/server/app.py (GET /api/braid — the bytes Copy and
 *              Download must both match exactly)
 * @design      PLAN2.md §4 M10, queue item K33
 */
import { useEffect, useState } from "react";
import { diagramLineCount, foldDiagram, renderBraidMarkdown, slugifyPlanName } from "./braidPreview";

export interface BraidModalProps {
  /** null while closed — App.tsx clears it back to null rather than
   * unmounting this component (see the header for why that's deliberate). */
  text: string | null;
  planName: string;
  onClose: () => void;
}

type View = "rendered" | "raw";

/** Build an `<a download>`, click it, and clean up — the standard no-server-
 * round-trip browser download idiom. `bytes` must be the untouched braid
 * string (never a folded/rendered display copy) so the saved file is
 * exactly what GET /api/braid would return, byte for byte. */
function downloadText(bytes: string, filename: string): void {
  const blob = new Blob([bytes], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // Deferred, not immediate: revoking in the same tick as click() has
  // shipped without incident elsewhere, but a 0ms timeout costs nothing and
  // guarantees the browser has already read the blob before the URL dies.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** The braid preview modal; renders nothing while `text` is null. */
export function BraidModal({ text, planName, onClose }: BraidModalProps) {
  // "Remember per session": plain state on an always-mounted component
  // (App.tsx never unmounts this — see the header) rather than localStorage
  // or a module-level variable — the cheapest thing that actually works.
  const [view, setView] = useState<View>("rendered");
  // Folded by default (judgment call, documented in braidPreview.ts's own
  // header): the roadmap's own diagram runs dozens of lines, and a preview
  // meant to "read as a document" should not open on a wall of mermaid
  // source. The toggle un-hides it on demand.
  const [showDiagram, setShowDiagram] = useState(false);
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  const diagramLines = text === null ? null : diagramLineCount(text);
  const hasDiagram = diagramLines !== null;
  const displayText = text === null ? "" : showDiagram || diagramLines === null ? text : foldDiagram(text);

  // Renders regardless of which view is active (not just while view ===
  // "rendered") so switching Raw -> Rendered is instant after the first
  // paint — only the very first call ever pays the dynamic-import cost.
  useEffect(() => {
    if (text === null) return;
    let cancelled = false;
    setRenderError(null);
    renderBraidMarkdown(displayText)
      .then((html) => {
        if (!cancelled) setRenderedHtml(html);
      })
      .catch((err: unknown) => {
        if (!cancelled) setRenderError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [text, displayText]);

  if (text === null) return null;

  return (
    <div className="kumi-modal" onClick={onClose}>
      <div className="kumi-modal-box kumi-braid-box" onClick={(event) => event.stopPropagation()}>
        <div className="kumi-braid-toolbar">
          <div className="kumi-braid-view-toggle" role="tablist" aria-label="Braid view">
            {(["rendered", "raw"] as const).map((candidate) => (
              <button
                key={candidate}
                role="tab"
                aria-selected={view === candidate}
                className={`kumi-braid-view-btn${view === candidate ? " kumi-braid-view-active" : ""}`}
                onClick={() => setView(candidate)}
              >
                {candidate === "rendered" ? "Rendered" : "Raw"}
              </button>
            ))}
          </div>
          {hasDiagram ? (
            <button
              className="kumi-braid-diagram-toggle"
              title="Mermaid itself is never rendered — this only shows or hides the fenced source"
              onClick={() => setShowDiagram((current) => !current)}
            >
              {showDiagram ? "Hide diagram" : "Show diagram"}
            </button>
          ) : null}
        </div>
        <div className="kumi-actions kumi-braid-actions">
          <button className="kumi-primary" onClick={() => void navigator.clipboard.writeText(text)}>
            Copy
          </button>
          <button onClick={() => downloadText(text, `${slugifyPlanName(planName)}.braid.md`)}>Download</button>
          <button onClick={onClose}>Close</button>
        </div>
        {view === "raw" ? (
          <pre className="kumi-braid">{displayText}</pre>
        ) : renderError ? (
          <p className="kumi-braid-error">
            Could not render Markdown ({renderError}).{" "}
            <button onClick={() => setView("raw")}>Switch to Raw</button>
          </p>
        ) : renderedHtml === null ? (
          <p className="kumi-braid-loading">Rendering…</p>
        ) : (
          // marked's raw-HTML passthrough is neutralized in
          // braidPreview.ts's renderer override before this ever runs —
          // see that file's own header for the verified XSS reasoning.
          <div className="kumi-braid-rendered" dangerouslySetInnerHTML={{ __html: renderedHtml }} />
        )}
      </div>
    </div>
  );
}
