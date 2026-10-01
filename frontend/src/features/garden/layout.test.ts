import { describe, expect, it } from "vitest";
import type { CheckpointNode } from "../../shared/types/contracts";
import { computeLayout, reachableCheckpoints } from "./layout";

function node(id: string, parent: string | null, depth: number): CheckpointNode {
  return { checkpoint_id: id, parent_id: parent, step_id: parent ? "s" : null, option_id: parent ? id : null, depth };
}

describe("layout", () => {
  it("returns nothing without a root", () => {
    expect(computeLayout([node("a", "x", 1)], 2).nodes).toHaveLength(0);
  });

  it("drops orphans and places depth on rings", () => {
    const cps = [node("r", null, 0), node("a", "r", 1), node("b", "a", 2), node("o", "missing", 1)];
    expect(reachableCheckpoints(cps)).toHaveLength(3);
    const { nodes, ringGap } = computeLayout(cps, 3);
    const b = nodes.find((n) => n.id === "b");
    expect(b?.radius).toBeCloseTo(2 * ringGap);
    expect(b?.isLeaf).toBe(true);
  });

  it("lays out 200 nodes", () => {
    const cps = [node("r", null, 0)];
    for (let i = 0; i < 199; i++) cps.push(node(`n${i}`, i < 10 ? "r" : `n${i % 10}`, i < 10 ? 1 : 2));
    expect(computeLayout(cps, 3).nodes).toHaveLength(200);
  });
});
