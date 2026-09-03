/**
 * @file        frontend/src/cones.test.ts
 * @purpose     vitest coverage for cones.ts's pure BFS graph math (K44,
 *              "cones/lanes if cheap" — cones.ts has no DOM/React and no
 *              container substitution to fake, so it's cheap): ancestor/
 *              descendant hop-distance, pathsBetween's both-orientation
 *              union, and containerCones' member-exclusion/closest-hop-wins
 *              union rule.
 * @layer       frontend
 * @tags        vitest, cones, bfs, focus, trace, mutation-proof
 * @related     frontend/src/cones.ts (the module under test)
 * @design      PLAN2.md §2.1, queue item K44
 */
import { describe, expect, it } from "vitest";
import { ancestorsOf, containerCones, descendantsOf, pathsBetween } from "./cones";
import type { PlanNode } from "./types";

function node(id: string, needs: string[] = []): PlanNode {
  return {
    digest: `digest-${id}`,
    id,
    kind: "task",
    title: id,
    needs,
    in: [],
    links: [],
    agents: [],
    skills: [],
    trains: [],
    priority: 0,
    fields: {},
    effective: {},
    body: "",
  };
}

// a -> b -> c -> d (c needs b, b needs a, d needs c): a straight chain, plus
// an unrelated island node "z" that touches nothing.
const chain = [node("a"), node("b", ["a"]), node("c", ["b"]), node("d", ["c"]), node("z")];

describe("ancestorsOf / descendantsOf", () => {
  it("reports hop distance along a chain, excluding the start node itself", () => {
    const ancestors = ancestorsOf(chain, "d");
    expect(ancestors.get("c")).toBe(1);
    expect(ancestors.get("b")).toBe(2);
    expect(ancestors.get("a")).toBe(3);
    expect(ancestors.has("d")).toBe(false);
    expect(ancestors.has("z")).toBe(false);
  });

  it("descendantsOf is the mirror of ancestorsOf along the same chain", () => {
    const descendants = descendantsOf(chain, "a");
    expect(descendants.get("b")).toBe(1);
    expect(descendants.get("c")).toBe(2);
    expect(descendants.get("d")).toBe(3);
    expect(descendants.has("a")).toBe(false);
  });

  it("returns an empty map for a node with no dependencies and no dependents", () => {
    expect(ancestorsOf(chain, "z").size).toBe(0);
    expect(descendantsOf(chain, "z").size).toBe(0);
  });

  it("takes the shorter hop distance when two paths reach the same node", () => {
    // e needs a directly (1 hop) AND needs d, which is 3 hops from a — the
    // direct edge must win, not the longer route through the chain.
    const withShortcut = [...chain, node("e", ["a", "d"])];
    const descendants = descendantsOf(withShortcut, "a");
    expect(descendants.get("e")).toBe(1);
  });
});

describe("pathsBetween", () => {
  it("finds every node on the needs-path between two ends, either order", () => {
    expect(pathsBetween(chain, "a", "d")).toEqual(new Set(["a", "b", "c", "d"]));
    expect(pathsBetween(chain, "d", "a")).toEqual(new Set(["a", "b", "c", "d"]));
  });

  it("returns the empty set for two nodes with no connecting path", () => {
    expect(pathsBetween(chain, "z", "a").size).toBe(0);
  });

  it("excludes a node that only branches off the path, not lying on it", () => {
    const withBranch = [...chain, node("branch", ["b"])]; // branch needs b, not on a->d
    const path = pathsBetween(withBranch, "a", "d");
    expect(path.has("branch")).toBe(false);
    expect(path).toEqual(new Set(["a", "b", "c", "d"]));
  });
});

describe("containerCones", () => {
  it("unions member cones and excludes the container's own members", () => {
    // upstream: x -> m1 (member "m") ; downstream: m2 (member) -> y
    const nodes = [node("x"), node("m"), node("m2", ["m", "x"]), node("y", ["m2"])];
    const result = containerCones(nodes, ["m", "m2"]);
    expect(result.ancestors.has("x")).toBe(true);
    expect(result.ancestors.has("m")).toBe(false); // own member, excluded
    expect(result.ancestors.has("m2")).toBe(false); // own member, excluded
    expect(result.descendants.has("y")).toBe(true);
  });

  it("keeps the closest hop distance when two members share an ancestor", () => {
    const nodes = [node("root"), node("near", ["root"]), node("far", ["near"]), node("m1", ["near"]), node("m2", ["far"])];
    const result = containerCones(nodes, ["m1", "m2"]);
    // "near" is 1 hop from m1 and 2 hops from m2 (via far) — the union must
    // keep the closer distance, not the last one computed.
    expect(result.ancestors.get("near")).toBe(1);
  });

  it("returns empty cones for a container whose members have no outside edges", () => {
    const nodes = [node("m1"), node("m2", ["m1"])];
    const result = containerCones(nodes, ["m1", "m2"]);
    expect(result.ancestors.size).toBe(0);
    expect(result.descendants.size).toBe(0);
  });
});
