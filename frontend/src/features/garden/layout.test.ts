import { describe, expect, it } from "vitest";
import type { CheckpointNode } from "../../shared/types/contracts";
import { computeLayout, reachableCheckpoints, WEDGE } from "./layout";

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
    const { nodes, radiusOf } = computeLayout(cps, 3);
    const b = nodes.find((n) => n.id === "b");
    expect(b?.radius).toBeCloseTo(radiusOf(2));
    expect(b?.isLeaf).toBe(true);
  });

  it("keeps branches out of the label wedge", () => {
    const cps = [node("r", null, 0), node("a", "r", 1), node("b", "r", 1), node("c", "r", 1)];
    const angles = computeLayout(cps, 2).nodes.filter((n) => n.depth === 1).map((n) => n.angle);
    for (const angle of angles) {
      expect(angle).toBeGreaterThanOrEqual(WEDGE / 2 - 1e-9);
      expect(angle).toBeLessThanOrEqual(2 * Math.PI - WEDGE / 2 + 1e-9);
    }
  });

  it("stretches x by the aspect ratio", () => {
    const cps = [node("r", null, 0), node("a", "r", 1)];
    const round = computeLayout(cps, 2, 200, 1).nodes[1];
    const wide = computeLayout(cps, 2, 200, 1.5).nodes[1];
    expect(wide?.x).toBeCloseTo((round?.x ?? 0) * 1.5);
    expect(wide?.y).toBeCloseTo(round?.y ?? 1);
  });

  it("lays out 200 nodes", () => {
    const cps = [node("r", null, 0)];
    for (let i = 0; i < 199; i++) cps.push(node(`n${i}`, i < 10 ? "r" : `n${i % 10}`, i < 10 ? 1 : 2));
    expect(computeLayout(cps, 3).nodes).toHaveLength(200);
  });
});
