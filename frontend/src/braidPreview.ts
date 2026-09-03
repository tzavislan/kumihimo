/**
 * @file        frontend/src/braidPreview.ts
 * @purpose     Pure/async support for BraidModal.tsx (K33): fold the braid's
 *              one "Plan shape" mermaid fence to a one-line affordance (Raw
 *              and Rendered share this transform), render the resulting text
 *              to sanitized HTML via a lazily-imported `marked` — never part
 *              of the initial bundle, fetched only the first time a render
 *              actually runs — and slug a plan name into a download
 *              filename. Nothing here ever touches the original braid string
 *              in place: every function returns a fresh DISPLAY copy: Copy
 *              and Download stay wired to BraidModal.tsx's untouched prop.
 *              Two deliberate deviations from marked's defaults keep node-
 *              body Markdown from ever producing a live or navigable hostile
 *              element: the `html` token hook escapes raw HTML instead of
 *              passing it through, and the `link`/`image` hooks apply a URL-
 *              scheme allow-list (checker-flagged gap, fixed same day: the
 *              html override alone left `[x](javascript:...)` and
 *              `<javascript:...>` autolinks rendering as live, clickable
 *              `<a>` elements — marked's own default link/image renderers do
 *              no scheme filtering at all).
 * @layer       frontend
 * @tags        markdown, marked, lazy-load, sanitize, xss, download
 * @related     frontend/src/BraidModal.tsx (the one caller),
 *              kumihimo/compile/templates/cord.j2 (the "## Plan shape"
 *              section and its one ```mermaid fence this folds),
 *              kumihimo/packs/engineering/templates/task.j2 (the `After`,
 *              `Assigned`, `With`, `Trains`, `Consult` single-newline
 *              metadata stack `breaks: true` below turns into real lines),
 *              frontend/vite.config.ts (base build config; manualChunks is
 *              K34's job — plain dynamic import() already gets `marked` its
 *              own chunk with zero config, verified in the K33 build log)
 * @design      PLAN2.md §4 M10, queue item K33
 */

// cord.j2 emits at most one "```mermaid\n...\n```" fence (the "Plan shape"
// section) — see that template's own header comment. A plan built with
// `compile.diagram: false` has none; diagramLineCount/foldDiagram both treat
// that as "nothing to fold," not an error.
const MERMAID_FENCE = /```mermaid\n([\s\S]*?)\n```/;

/** Lines inside the braid's one mermaid fence, or null when it has none —
 * BraidModal.tsx hides the Diagram toggle entirely when this is null. */
export function diagramLineCount(text: string): number | null {
  const match = MERMAID_FENCE.exec(text);
  return match ? match[1].split("\n").length : null;
}

/**
 * Replace the mermaid fence's body with a one-line fold affordance; the
 * fence markers stay, so a folded diagram still reads as a code block in
 * both Raw's <pre> and Rendered's marked output — mermaid itself is never
 * rendered here (that's ~1MB of dependency, out of budget against K34).
 * A no-op (returns `text` unchanged) when there's nothing to fold.
 */
export function foldDiagram(text: string): string {
  return text.replace(MERMAID_FENCE, (_whole, body: string) => {
    const lines = body.split("\n").length;
    return `\`\`\`mermaid\n(plan-shape diagram hidden — ${lines} line${lines === 1 ? "" : "s"})\n\`\`\``;
  });
}

/** id-slug a plan's display name for a download filename: lowercase,
 * non-alphanumeric runs collapsed to one hyphen, leading/trailing hyphens
 * trimmed; "braid" when that leaves nothing (an empty or purely-symbolic
 * plan name) so a download is never handed an empty filename stem. */
export function slugifyPlanName(name: string): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "braid";
}

function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// A link may open in the reader's browser; an image src is fetched
// unconditionally the moment it renders. Deny-by-default: only these
// schemes (plus a relative reference, which has none) are ever wired into a
// live href/src — everything else, including javascript:/data:/vbscript:
// and any scheme we've never heard of, degrades to inert text instead
// (isSafeUrl below, called with one of these two sets), same philosophy as
// the html escape above. Images additionally exclude mailto: (meaningless
// there) and, per the checker's own call, data: too — a data: image is a
// legitimate case in general, but this preview holds a stricter line on
// purpose rather than special-casing it back in.
const ALLOWED_LINK_SCHEMES = new Set(["http:", "https:", "mailto:"]);
const ALLOWED_IMAGE_SCHEMES = new Set(["http:", "https:"]);

/**
 * The URL's scheme, lowercased with its trailing ":" (e.g. "javascript:"),
 * or null when there's no colon before the first `/`, `?`, or `#` — i.e. a
 * relative reference (a bare path, a `?query`, or a `#fragment`), which
 * every caller here always allows.
 *
 * @purpose  Matches the WHATWG URL parser's own preprocessing (strip every
 *           TAB/LF/CR wherever it falls, then leading C0-control-or-space)
 *           before looking for the scheme, so a scheme hidden behind
 *           "j\navascript:" or a leading control character — both still
 *           live javascript: URLs to a real browser, since that's exactly
 *           what it strips before parsing — can't slip past a check that
 *           only trims the string's own ends. A colon that shows up AFTER
 *           the first /?# (e.g. "/search?q=javascript:x") is correctly read
 *           as part of the path/query, not a scheme, and always allowed.
 */
function urlScheme(url: string): string | null {
  const noTabOrNewline = url.replace(/[\t\n\r]/g, "");
  let start = 0;
  while (start < noTabOrNewline.length && noTabOrNewline.charCodeAt(start) <= 32) start++;
  const normalized = noTabOrNewline.slice(start);
  const stop = normalized.search(/[/?#]/);
  const head = stop === -1 ? normalized : normalized.slice(0, stop);
  const colon = head.indexOf(":");
  return colon === -1 ? null : head.slice(0, colon + 1).toLowerCase();
}

function isSafeUrl(url: string, allowed: Set<string>): boolean {
  const scheme = urlScheme(url);
  return scheme === null || allowed.has(scheme);
}

// Type-only: `typeof import(...)` is erased at compile time, so this alone
// does not pull `marked` into whatever chunk this file lands in — only the
// value-level `await import("marked")` inside renderBraidMarkdown does that,
// and only when it actually runs.
type MarkedModule = typeof import("marked");
let markedSingleton: MarkedModule["marked"] | null = null;

/**
 * Render braid Markdown to HTML safe to hand to dangerouslySetInnerHTML.
 *
 * @purpose  marked's true factory default PASSES raw HTML in the source
 *           straight through to its output — verified directly against this
 *           exact pinned version (package.json): a node body containing
 *           `<script>alert(1)</script>` or `<img src=x onerror="...">`
 *           renders live and would execute. There is no "sanitize" option
 *           any more (removed upstream), so instead the renderer's own
 *           `html` token hook — called for both block- and inline-level raw
 *           HTML — is overridden here to HTML-escape the text instead of
 *           passing it through; re-verify this with the same two payloads
 *           if this package is ever upgraded. Every other Markdown construct
 *           (headings, lists, code, tables, blockquotes, GFM task-list
 *           checkboxes) is untouched — this is the one deliberate deviation
 *           from marked's defaults, not a general sanitizer swap-in.
 *           A second, independent gap the `html` override does NOT close:
 *           marked's default `link`/`image` renderers apply zero scheme
 *           filtering — `[x](javascript:alert(1))` and the CommonMark
 *           autolink `<javascript:alert(1)>` both render as a live, clickable
 *           `<a href="javascript:alert(1)">` by default, confirmed by
 *           clicking one in a real running instance of this app. `link` and
 *           `image` are therefore ALSO overridden, hand-assembling the tag
 *           only when isSafeUrl passes the appropriate allow-list
 *           (ALLOWED_LINK_SCHEMES/ALLOWED_IMAGE_SCHEMES above); otherwise
 *           the link/image's own inline content renders with no `<a>`/`<img>`
 *           wrapper at all — inert text (formatting like `**bold**` inside a
 *           denied link still renders; it just isn't wrapped in a live
 *           element), never a live or navigable element. href/src/title are
 *           hand-escaped here too (escapeHtml, not marked's own internal
 *           href-cleaning, since this bypasses it entirely) since a quote in
 *           an otherwise-allowed URL could break out of the attribute.
 *           `breaks: true` because the engineering pack's own task/decision/
 *           risk/question templates stack `After`, `Assigned`, `With`,
 *           `Trains`, `Consult` as consecutive single-newline-separated
 *           lines with no blank line between them (see task.j2) —
 *           CommonMark's own default would run every one of those together
 *           onto one visual line per item, which is a readability
 *           regression on every single task in every braid. The trade:
 *           hand-wrapped prose in a node body (examples/apiguard's bodies do
 *           this) picks up one extra line break per wrapped source line —
 *           a much smaller, purely cosmetic cost, and not present at all in
 *           this repo's own dogfooded plan (plans/roadmap's bodies are
 *           unwrapped). Configured once (the module-level singleton above):
 *           repeat calls, across as many modal opens as one session makes,
 *           must not re-wrap the renderer override each time.
 */
export async function renderBraidMarkdown(text: string): Promise<string> {
  if (!markedSingleton) {
    const { marked } = await import("marked");
    marked.use({
      breaks: true,
      renderer: {
        html({ text: rawHtml }) {
          return escapeHtml(rawHtml);
        },
        // label is already fully rendered+escaped HTML here (parseInline
        // with the DEFAULT renderer, same as marked's own link() does) —
        // used as-is below, never escaped a second time. The !tokens
        // fallback (defensive; every real link/autolink token carried
        // `tokens` in testing) escapes the raw `text` field once instead.
        link({ href, title, text: rawText, tokens }) {
          const label = tokens ? this.parser.parseInline(tokens) : escapeHtml(rawText);
          if (!isSafeUrl(href, ALLOWED_LINK_SCHEMES)) return label;
          const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
          return `<a href="${escapeHtml(href)}"${titleAttr}>${label}</a>`;
        },
        // label is RAW here (parseInline with the plain TextRenderer, which
        // returns text unescaped — alt text can't carry markup, only plain
        // text) — escaped once at each point it's actually used below.
        image({ href, title, text: rawText, tokens }) {
          const label = tokens ? this.parser.parseInline(tokens, this.parser.textRenderer) : rawText;
          if (!isSafeUrl(href, ALLOWED_IMAGE_SCHEMES)) return escapeHtml(label);
          const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
          return `<img src="${escapeHtml(href)}" alt="${escapeHtml(label)}"${titleAttr}>`;
        },
      },
    });
    markedSingleton = marked;
  }
  return markedSingleton.parse(text, { async: false });
}
