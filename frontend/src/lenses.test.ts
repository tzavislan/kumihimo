/**
 * @file        frontend/src/lenses.test.ts
 * @purpose     vitest coverage for lenses.ts's pure crew math (K44):
 *              crewTextColor checked against an INDEPENDENT WCAG relative-
 *              luminance/contrast-ratio implementation (re-derived here from
 *              the spec, not imported — a shared bug in both would otherwise
 *              agree with itself and prove nothing), swept across a grid of
 *              hue/saturation/lightness including the exact regression the
 *              source file's own comment documents (hue ~90-165 tints
 *              failing white text at 1.9-2.3:1); crewLens's golden-angle hue
 *              assignment for stability (sorted-id determinism, insertion-
 *              order independence) and its unassigned-work rule (K41.1's
 *              done-task exception).
 * @layer       frontend
 * @tags        vitest, lenses, crew, wcag, contrast, hue, mutation-proof
 * @related     frontend/src/lenses.ts (the module under test),
 *              frontend/src/types.ts (PlanNode — the fixture shape below)
 * @design      PLAN2.md §3, queue item K44
 */
import { describe, expect, it } from "vitest";
import { crewLens, crewTextColor } from "./lenses";
import type { PlanNode } from "./types";

// -------------------------------------------------------------------------
// An independent WCAG 2.x implementation — deliberately NOT lenses.ts's own
// relativeLuminance/contrastRatio/hslToRgb (private anyway), re-derived from
// the spec text so this test can't silently agree with a shared bug.
// -------------------------------------------------------------------------

function refHslToRgb(h: number, s: number, l: number): [number, number, number] {
  // Standard HSL->RGB (CSS Color 4 / Wikipedia's own formula), s/l in 0-1.
  const a = s * Math.min(l, 1 - l);
  const f = (n: number): number => {
    const k = (n + h / 30) % 12;
    return l - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)));
  };
  return [Math.round(f(0) * 255), Math.round(f(8) * 255), Math.round(f(4) * 255)];
}

function refRelativeLuminance(r: number, g: number, b: number): number {
  const chan = (c: number): number => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b);
}

function refContrast(l1: number, l2: number): number {
  const [hi, lo] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

/** The reference "which of black/white reads better" answer, entirely
 * independent of lenses.ts's own crewTextColor. */
function refBestTextColor(h: number, sPct: number, lPct: number): "#ffffff" | "#000000" {
  const [r, g, b] = refHslToRgb(h, sPct / 100, lPct / 100);
  const bg = refRelativeLuminance(r, g, b);
  const white = refContrast(bg, 1);
  const black = refContrast(bg, 0);
  return white >= black ? "#ffffff" : "#000000";
}

describe("crewTextColor vs an independent WCAG implementation", () => {
  it("agrees with the reference formula at the boundaries", () => {
    expect(crewTextColor(0, 0, 0)).toBe(refBestTextColor(0, 0, 0)); // pure black bg
    expect(crewTextColor(0, 0, 0)).toBe("#ffffff");
    expect(crewTextColor(0, 0, 100)).toBe(refBestTextColor(0, 0, 100)); // pure white bg
    expect(crewTextColor(0, 0, 100)).toBe("#000000");
  });

  it("agrees with the reference formula on the documented regression case (hue ~90-165)", () => {
    // lenses.ts's own comment: these tints (crewLens's actual agent-self and
    // mentioned-by parameter pairs) failed white text at 1.9-2.3:1 before
    // the fix — both must resolve to whichever the reference formula picks,
    // not a hardcoded assumption of which color that is.
    for (const [h, s, l] of [
      [90, 70, 45],
      [120, 70, 45],
      [150, 70, 45],
      [90, 55, 60],
      [120, 55, 60],
      [150, 55, 60],
      [165, 55, 60],
    ] as const) {
      expect(crewTextColor(h, s, l)).toBe(refBestTextColor(h, s, l));
    }
  });

  it("agrees with the reference formula across a broad hue/sat/light grid", () => {
    // A property-style sweep: any subtle threshold/luminance-weight bug in
    // crewTextColor is very likely to disagree with the independent formula
    // somewhere in a grid this size, even if it happens to agree at a few
    // hand-picked points.
    let checked = 0;
    for (let h = 0; h < 360; h += 24) {
      for (const s of [20, 55, 70, 100]) {
        for (const l of [10, 30, 45, 60, 75, 90]) {
          expect(crewTextColor(h, s, l)).toBe(refBestTextColor(h, s, l));
          checked += 1;
        }
      }
    }
    expect(checked).toBeGreaterThan(300);
  });
});

// -------------------------------------------------------------------------
// crewLens: golden-angle hue assignment stability + the unassigned rule.
// -------------------------------------------------------------------------

const GOLDEN_ANGLE = 137.508; // mirrors lenses.ts's own documented constant

function node(overrides: Partial<PlanNode> & Pick<PlanNode, "id" | "kind">): PlanNode {
  return {
    digest: `digest-${overrides.id}`,
    title: overrides.id,
    needs: [],
    in: [],
    links: [],
    agents: [],
    skills: [],
    trains: [],
    priority: 0,
    fields: {},
    effective: {},
    body: "",
    ...overrides,
  };
}

/** Pull {h, s, l} back out of crewLens's "hsl(h, s%, l%)" tint string. */
function parseHsl(color: string): { h: number; s: number; l: number } {
  const match = /^hsl\(([-\d.]+), (\d+)%, (\d+)%\)$/.exec(color);
  if (!match) throw new Error(`not an hsl() string: ${color}`);
  return { h: Number(match[1]), s: Number(match[2]), l: Number(match[3]) };
}

describe("crewLens hue assignment", () => {
  it("assigns hues by golden-angle rotation over SORTED agent ids", () => {
    const nodes = [node({ id: "zebra-agent", kind: "agent" }), node({ id: "alpha-agent", kind: "agent" })];
    const result = crewLens(nodes);
    // Sorted order is alpha-agent (index 0), zebra-agent (index 1) —
    // regardless of the array's own insertion order above.
    expect(parseHsl(result.tint.get("alpha-agent")!.color).h).toBeCloseTo(0, 6);
    expect(parseHsl(result.tint.get("zebra-agent")!.color).h).toBeCloseTo(GOLDEN_ANGLE % 360, 6);
  });

  it("is deterministic across repeated calls and independent of array order", () => {
    const forward = [node({ id: "a", kind: "agent" }), node({ id: "b", kind: "agent" }), node({ id: "c", kind: "agent" })];
    const reversed = [...forward].reverse();
    const first = crewLens(forward);
    const second = crewLens(forward);
    const fromReversed = crewLens(reversed);
    for (const id of ["a", "b", "c"]) {
      expect(first.tint.get(id)!.color).toBe(second.tint.get(id)!.color);
      expect(first.tint.get(id)!.color).toBe(fromReversed.tint.get(id)!.color);
    }
  });

  it("gives a mentioning node the same hue as its first agent, at a softer tint", () => {
    const nodes = [
      node({ id: "bot", kind: "agent" }),
      node({ id: "t1", kind: "task", agents: ["bot"], effective: { status: "todo" } }),
    ];
    const result = crewLens(nodes);
    const agentTint = parseHsl(result.tint.get("bot")!.color);
    const taskTint = parseHsl(result.tint.get("t1")!.color);
    expect(taskTint.h).toBeCloseTo(agentTint.h, 6);
    // Agent-self: stronger (70%, 45%); mentioned-by: softer (55%, 60%) —
    // lenses.ts's own crewLens parameters, asserted here as a contract.
    expect(agentTint).toMatchObject({ s: 70, l: 45 });
    expect(taskTint).toMatchObject({ s: 55, l: 60 });
  });

  it("leaves a node with no agent mention and no agent kind untinted", () => {
    const nodes = [node({ id: "bot", kind: "agent" }), node({ id: "lonely", kind: "task" })];
    const result = crewLens(nodes);
    expect(result.tint.has("lonely")).toBe(false);
  });
});

describe("crewLens unassigned-work rule (K41.1)", () => {
  it("flags a todo task with no agents", () => {
    const result = crewLens([node({ id: "t1", kind: "task", effective: { status: "todo" } })]);
    expect(result.unassigned.has("t1")).toBe(true);
  });

  it("does not flag a DONE task with no agents", () => {
    const result = crewLens([node({ id: "t1", kind: "task", effective: { status: "done" } })]);
    expect(result.unassigned.has("t1")).toBe(false);
  });

  it("does not flag a task that already has an agent, regardless of status", () => {
    const result = crewLens([
      node({ id: "t1", kind: "task", agents: ["bot"], effective: { status: "todo" } }),
      node({ id: "bot", kind: "agent" }),
    ]);
    expect(result.unassigned.has("t1")).toBe(false);
  });

  it("never flags a non-task kind, agentless or not", () => {
    const result = crewLens([node({ id: "m1", kind: "milestone", effective: { status: "todo" } })]);
    expect(result.unassigned.has("m1")).toBe(false);
  });
});
