/**
 * @file        frontend/src/braidPreview.test.ts
 * @purpose     vitest coverage for braidPreview.ts's pure helpers (K44):
 *              decodeColonEntities' three entity forms (decimal/hex/named,
 *              case and leading-zero variants), urlScheme/isSafeUrl as an
 *              allow/deny table over both schemes sets — plain schemes,
 *              relative references, the entity-hidden and whitespace-hidden
 *              javascript: tricks (K43.1) — diagramLineCount/foldDiagram's
 *              line counting, and slugifyPlanName's filename rules.
 * @layer       frontend
 * @tags        vitest, braid-preview, xss, url-scheme, entities, mutation-proof
 * @related     frontend/src/braidPreview.ts (the module under test)
 * @design      PLAN2.md §4 M10, queue items K33, K43.1, K44
 */
import { describe, expect, it } from "vitest";
import {
  ALLOWED_IMAGE_SCHEMES,
  ALLOWED_LINK_SCHEMES,
  decodeColonEntities,
  diagramLineCount,
  foldDiagram,
  isSafeUrl,
  slugifyPlanName,
  urlScheme,
} from "./braidPreview";

describe("decodeColonEntities", () => {
  it.each([
    ["decimal", "javascript&#58;alert(1)", "javascript:alert(1)"],
    ["decimal with leading zeros", "javascript&#058;alert(1)", "javascript:alert(1)"],
    ["decimal with more leading zeros", "javascript&#0058;alert(1)", "javascript:alert(1)"],
    ["hex lowercase", "javascript&#x3a;alert(1)", "javascript:alert(1)"],
    ["hex uppercase digit+x", "javascript&#X3A;alert(1)", "javascript:alert(1)"],
    ["hex mixed case", "javascript&#x3A;alert(1)", "javascript:alert(1)"],
    ["hex with leading zero", "javascript&#x03a;alert(1)", "javascript:alert(1)"],
    ["named", "javascript&colon;alert(1)", "javascript:alert(1)"],
    ["named uppercase", "javascript&COLON;alert(1)", "javascript:alert(1)"],
  ])("decodes %s form", (_label, input, expected) => {
    expect(decodeColonEntities(input)).toBe(expected);
  });

  it("decodes every occurrence, not just the first", () => {
    expect(decodeColonEntities("a&#58;b&colon;c&#x3a;d")).toBe("a:b:c:d");
  });

  it("leaves non-colon entities and plain text untouched", () => {
    expect(decodeColonEntities("Tom &amp; Jerry")).toBe("Tom &amp; Jerry");
    expect(decodeColonEntities("no entities here")).toBe("no entities here");
  });

  it("does not decode a bare numeric reference with no trailing semicolon", () => {
    // Documented scope limit (braidPreview.ts's own comment): only the
    // trailing-";" forms are recognized here.
    expect(decodeColonEntities("javascript&#58alert(1)")).toBe("javascript&#58alert(1)");
  });
});

describe("urlScheme / isSafeUrl: allow/deny table", () => {
  const cases: Array<[string, string, boolean, boolean]> = [
    // [url, scheme label, allowed as a link, allowed as an image]
    ["http://example.com/x", "http:", true, true],
    ["https://example.com/x", "https:", true, true],
    ["HTTPS://EXAMPLE.COM/x", "https: (uppercase)", true, true],
    ["mailto:a@b.com", "mailto: (link only)", true, false],
    ["javascript:alert(1)", "javascript:", false, false],
    ["JavaScript:alert(1)", "javascript: (mixed case)", false, false],
    ["vbscript:msgbox(1)", "vbscript:", false, false],
    ["data:image/png;base64,Zm9v", "data: (excluded even for images)", false, false],
    ["ftp://example.com/x", "ftp: (never allow-listed)", false, false],
  ];

  it.each(cases)("%s -> link=%s image=%s", (url, _label, linkOk, imageOk) => {
    expect(isSafeUrl(url, ALLOWED_LINK_SCHEMES)).toBe(linkOk);
    expect(isSafeUrl(url, ALLOWED_IMAGE_SCHEMES)).toBe(imageOk);
  });

  it("treats a relative reference (no scheme) as always safe", () => {
    for (const url of ["/search?q=1", "?query=1", "#fragment", "foo/bar", "", "./relative"]) {
      expect(urlScheme(url)).toBeNull();
      expect(isSafeUrl(url, ALLOWED_LINK_SCHEMES)).toBe(true);
      expect(isSafeUrl(url, ALLOWED_IMAGE_SCHEMES)).toBe(true);
    }
  });

  it("reads a colon appearing after the first /?# as path/query, not a scheme", () => {
    expect(urlScheme("/search?q=javascript:x")).toBeNull();
    expect(isSafeUrl("/search?q=javascript:x", ALLOWED_LINK_SCHEMES)).toBe(true);
  });

  it("denies a scheme hidden behind an HTML colon-entity (K43.1)", () => {
    expect(urlScheme("javascript&#58;alert(1)")).toBe("javascript:");
    expect(isSafeUrl("javascript&#58;alert(1)", ALLOWED_LINK_SCHEMES)).toBe(false);
    expect(isSafeUrl("javascript&#x3a;alert(1)", ALLOWED_LINK_SCHEMES)).toBe(false);
    expect(isSafeUrl("javascript&colon;alert(1)", ALLOWED_LINK_SCHEMES)).toBe(false);
  });

  it.each([
    ["a tab inside the scheme", "java\tscript:alert(1)"],
    ["a newline inside the scheme", "java\nscript:alert(1)"],
    ["a carriage return inside the scheme", "java\rscript:alert(1)"],
    ["leading whitespace", "   javascript:alert(1)"],
    ["a leading C0 control character", "javascript:alert(1)"],
    ["leading whitespace plus a tab-split scheme", "  java\tscript:alert(1)"],
  ])("denies the whitespace trick: %s", (_label, url) => {
    expect(urlScheme(url)).toBe("javascript:");
    expect(isSafeUrl(url, ALLOWED_LINK_SCHEMES)).toBe(false);
  });

  it("still allows a normal http(s) URL padded with the same whitespace tricks", () => {
    expect(isSafeUrl("  http://example.com", ALLOWED_LINK_SCHEMES)).toBe(true);
    expect(isSafeUrl("ht\ttp://example.com", ALLOWED_LINK_SCHEMES)).toBe(true);
  });
});

describe("diagramLineCount / foldDiagram", () => {
  const withFence = "# Braid\n\n## Plan shape\n\n```mermaid\ngraph TD\nA-->B\nB-->C\n```\n\nMore text.\n";

  it("counts the mermaid fence's lines", () => {
    expect(diagramLineCount(withFence)).toBe(3); // "graph TD", "A-->B", "B-->C"
  });

  it("returns null when there is no mermaid fence", () => {
    expect(diagramLineCount("# Braid\n\nNo diagram here.\n")).toBeNull();
  });

  it("counts a single-line fence as 1", () => {
    expect(diagramLineCount("```mermaid\ngraph TD\n```\n")).toBe(1);
  });

  it("folds the fence body to a one-line affordance, plural, and leaves the rest untouched", () => {
    const folded = foldDiagram(withFence);
    expect(folded).toContain("```mermaid\n(plan-shape diagram hidden — 3 lines)\n```");
    expect(folded).toContain("# Braid");
    expect(folded).toContain("More text.");
    expect(folded).not.toContain("graph TD");
  });

  it("uses the singular 'line' for a one-line fence", () => {
    const folded = foldDiagram("```mermaid\ngraph TD\n```\n");
    expect(folded).toContain("(plan-shape diagram hidden — 1 line)");
  });

  it("is a no-op when there is nothing to fold", () => {
    const text = "# Braid\n\nNo diagram here.\n";
    expect(foldDiagram(text)).toBe(text);
  });
});

describe("slugifyPlanName", () => {
  it.each([
    ["My Plan!", "my-plan"],
    ["  --Foo--  ", "foo"],
    ["a___b   c", "a-b-c"],
    ["already-slug", "already-slug"],
    ["Crew Demo", "crew-demo"],
    ["100% Done", "100-done"],
  ])("slugifies %j to %j", (input, expected) => {
    expect(slugifyPlanName(input)).toBe(expected);
  });

  it.each([["", "braid"], ["!!!", "braid"], ["   ", "braid"], ["---", "braid"]])(
    "falls back to 'braid' for %j",
    (input, expected) => {
      expect(slugifyPlanName(input)).toBe(expected);
    },
  );
});
