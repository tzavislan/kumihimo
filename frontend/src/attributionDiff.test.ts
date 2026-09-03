/**
 * @file        frontend/src/attributionDiff.test.ts
 * @purpose     vitest coverage for attributionDiff.ts's diffLivePayload (K44):
 *              added/updated/removed classification, per-event claiming in
 *              file order with title-based dedupe (a rename's old-removed/
 *              new-added pair collapsing to one toast), actor->prefix mapping
 *              including the unmapped-actor fallback, actor "editor" claiming
 *              silently (no toast, no pulse), the "outside edit" fallback for
 *              whatever no event explains, a removed node never pulsing, and
 *              a hidden member's pulse substituting onto its collapsed
 *              container. Every fixture goes through the one exported entry
 *              point — the internal digestDiff/toastText/pulseTargets helpers
 *              are private on purpose (this file's own header note).
 * @layer       frontend
 * @tags        vitest, attribution, events, diff, mutation-proof
 * @related     frontend/src/attributionDiff.ts (the module under test),
 *              frontend/src/types.ts (Payload/PlanNode/EventLogEntry — the
 *              fixture shapes below)
 * @design      PLAN2.md §2.5 Motion & attribution, queue item K44
 */
import { describe, expect, it } from "vitest";
import { diffLivePayload } from "./attributionDiff";
import type { EventLogEntry, Payload, PlanNode } from "./types";

function node(overrides: Partial<PlanNode> & Pick<PlanNode, "id">): PlanNode {
  return {
    digest: `digest-${overrides.id}-1`,
    kind: "task",
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

function payload(nodes: PlanNode[], opts: { collapsed?: string[]; events?: EventLogEntry[] } = {}): Payload {
  return {
    plan: "Fixture",
    description: "",
    strategy: "grouped",
    kinds: {},
    nodes,
    findings: [],
    layout: {},
    collapsed: opts.collapsed ?? [],
    events: opts.events,
  };
}

const t1v1 = node({ id: "t1", title: "Guard the API" });
const t1v2 = { ...t1v1, digest: "digest-t1-2" };

describe("diffLivePayload: baseline and no-op cases", () => {
  it("returns nothing when there is no previous payload (the socket's first message)", () => {
    const result = diffLivePayload(null, payload([t1v1]));
    expect(result.toastTexts).toEqual([]);
    expect(result.pulseIds.size).toBe(0);
  });

  it("returns nothing when nothing actually changed", () => {
    const result = diffLivePayload(payload([t1v1]), payload([t1v1]));
    expect(result.toastTexts).toEqual([]);
    expect(result.pulseIds.size).toBe(0);
  });
});

describe("diffLivePayload: classification and actor mapping", () => {
  it("an added node claimed by a cli event toasts and pulses it", () => {
    const previous = payload([]);
    const incoming = payload([t1v1], { events: [{ actor: "cli", op: "add", targets: ["t1"] }] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via CLI: Guard the API added"]);
    expect(result.pulseIds).toEqual(new Set(["t1"]));
  });

  it("an updated node claimed by an mcp event toasts and pulses it", () => {
    const previous = payload([t1v1]);
    const incoming = payload([t1v2], { events: [{ actor: "mcp", op: "set", targets: ["t1"] }] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via MCP: Guard the API updated"]);
    expect(result.pulseIds).toEqual(new Set(["t1"]));
  });

  it("a removed node is named in its toast but never pulsed (nothing left to animate)", () => {
    const previous = payload([t1v1]);
    const incoming = payload([], { events: [{ actor: "cli", op: "remove", targets: ["t1"] }] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via CLI: Guard the API removed"]);
    expect(result.pulseIds.size).toBe(0);
  });

  it("an unmapped actor falls back to the generic API prefix", () => {
    const previous = payload([t1v1]);
    const incoming = payload([t1v2], { events: [{ actor: "webhook", op: "set", targets: ["t1"] }] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via API: Guard the API updated"]);
  });

  it("actor 'editor' claims its targets silently: no toast, no pulse", () => {
    const previous = payload([t1v1]);
    const incoming = payload([t1v2], { events: [{ actor: "editor", op: "set", targets: ["t1"] }] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual([]);
    expect(result.pulseIds.size).toBe(0);
  });

  it("a change no event explains falls back to 'outside edit' and still pulses", () => {
    const previous = payload([t1v1]);
    const incoming = payload([t1v2], { events: [] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["outside edit: Guard the API updated"]);
    expect(result.pulseIds).toEqual(new Set(["t1"]));
  });

  it("preserves file order across multiple disjoint claiming events", () => {
    const a1 = node({ id: "a", title: "Alpha" });
    const b1 = node({ id: "b", title: "Beta" });
    const previous = payload([a1, b1]);
    const incoming = payload([{ ...a1, digest: "a-2" }, { ...b1, digest: "b-2" }], {
      events: [
        { actor: "mcp", op: "set", targets: ["b"] },
        { actor: "cli", op: "set", targets: ["a"] },
      ],
    });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via MCP: Beta updated", "via CLI: Alpha updated"]);
  });
});

describe("diffLivePayload: dedupe and grouping", () => {
  it("dedupes a rename's old-removed/new-added ids sharing one title into one 'changed' toast", () => {
    const oldNode = node({ id: "old-id", title: "Core Service" });
    const newNode = node({ id: "new-id", title: "Core Service" });
    const previous = payload([oldNode]);
    const incoming = payload([newNode], {
      events: [{ actor: "cli", op: "rename", targets: ["old-id", "new-id"] }],
    });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via CLI: Core Service changed"]);
  });

  it("truncates a large claim to 3 names plus a '+n more' count", () => {
    const previous = payload([]);
    const ids = ["n1", "n2", "n3", "n4", "n5"];
    const nodes = ids.map((id, i) => node({ id, title: `Node ${i + 1}` }));
    const incoming = payload(nodes, { events: [{ actor: "cli", op: "add", targets: ids }] });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via CLI: Node 1, Node 2, Node 3 +2 more added"]);
  });

  it("an event claiming no changed ids contributes no toast and does not consume unclaimed ids", () => {
    const previous = payload([t1v1]);
    const incoming = payload([t1v2], {
      events: [
        { actor: "cli", op: "set", targets: ["unrelated-id"] },
        { actor: "mcp", op: "set", targets: ["t1"] },
      ],
    });
    const result = diffLivePayload(previous, incoming);
    expect(result.toastTexts).toEqual(["via MCP: Guard the API updated"]);
  });
});

describe("diffLivePayload: collapsed-container pulse substitution", () => {
  it("substitutes a hidden member's pulse onto its collapsed container", () => {
    const container = node({ id: "m1", kind: "milestone", title: "Milestone" });
    const memberV1 = node({ id: "t1", title: "Guard the API", in: ["m1"] });
    const memberV2 = { ...memberV1, digest: "digest-t1-2" };
    const previous = payload([container, memberV1]);
    const incoming = payload([container, memberV2], {
      collapsed: ["m1"],
      events: [{ actor: "cli", op: "set", targets: ["t1"] }],
    });
    const result = diffLivePayload(previous, incoming);
    // The toast still names the real node by its own title...
    expect(result.toastTexts).toEqual(["via CLI: Guard the API updated"]);
    // ...but the pulse lands on the collapsed container, not the hidden member.
    expect(result.pulseIds).toEqual(new Set(["m1"]));
  });

  it("pulses the member directly when its container is not collapsed", () => {
    const container = node({ id: "m1", kind: "milestone", title: "Milestone" });
    const memberV1 = node({ id: "t1", title: "Guard the API", in: ["m1"] });
    const memberV2 = { ...memberV1, digest: "digest-t1-2" };
    const previous = payload([container, memberV1]);
    const incoming = payload([container, memberV2], {
      collapsed: [],
      events: [{ actor: "cli", op: "set", targets: ["t1"] }],
    });
    const result = diffLivePayload(previous, incoming);
    expect(result.pulseIds).toEqual(new Set(["t1"]));
  });
});
