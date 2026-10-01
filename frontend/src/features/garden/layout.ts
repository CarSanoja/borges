import { stratify, tree } from "d3-hierarchy";
import type { CheckpointNode } from "../../shared/types/contracts";

export const DEFAULT_RADIUS = 300;
export const ROOT_RADIUS = 12;
export const WEDGE = (66 * Math.PI) / 180;
const INNER_SHARE = 0.27;

export interface GardenLayoutNode {
  id: string;
  parentId: string | null;
  stepId: string | null;
  optionId: string | null;
  depth: number;
  angle: number;
  radius: number;
  x: number;
  y: number;
  isLeaf: boolean;
}

export interface GardenLayout {
  nodes: GardenLayoutNode[];
  ringGap: number;
  innerRadius: number;
  aspect: number;
  maxDepth: number;
  radiusOf: (depth: number) => number;
}

const NO_LAYOUT: GardenLayout = {
  nodes: [],
  ringGap: 0,
  innerRadius: 0,
  aspect: 1,
  maxDepth: 0,
  radiusOf: () => 0,
};

export function reachableCheckpoints(checkpoints: CheckpointNode[]): CheckpointNode[] {
  const root = checkpoints.find((c) => c.parent_id === null);
  if (!root) return [];
  const seen = new Set<string>([root.checkpoint_id]);
  const kept: CheckpointNode[] = [root];
  const rest = checkpoints
    .filter((c) => c !== root && c.parent_id !== null)
    .sort((a, b) => a.depth - b.depth);
  for (const c of rest) {
    if (seen.has(c.checkpoint_id) || !seen.has(c.parent_id as string)) continue;
    seen.add(c.checkpoint_id);
    kept.push(c);
  }
  return kept;
}

export function pointAt(angle: number, radius: number, aspect = 1): { x: number; y: number } {
  return { x: radius * aspect * Math.sin(angle), y: -radius * Math.cos(angle) };
}

export function computeLayout(
  checkpoints: CheckpointNode[],
  stepCount: number,
  outerRadius: number = DEFAULT_RADIUS,
  aspect = 1,
): GardenLayout {
  const kept = reachableCheckpoints(checkpoints);
  if (kept.length === 0) return NO_LAYOUT;
  const root = stratify<CheckpointNode>()
    .id((d) => d.checkpoint_id)
    .parentId((d) => d.parent_id)(kept);
  const maxDepth = root.height;
  const rings = Math.max(stepCount, maxDepth, 1);
  const innerRadius = outerRadius * INNER_SHARE;
  const ringGap = rings > 1 ? (outerRadius - innerRadius) / (rings - 1) : outerRadius - innerRadius;
  const radiusOf = (depth: number) => (depth === 0 ? 0 : innerRadius + (depth - 1) * ringGap);
  const laidOut = tree<CheckpointNode>()
    .size([2 * Math.PI - WEDGE, 1])
    .separation((a, b) => (a.parent === b.parent ? 1 : 1.5) / Math.max(a.depth, 1))(root);
  const nodes: GardenLayoutNode[] = laidOut.descendants().map((n) => {
    const data = n.data;
    const radius = radiusOf(n.depth);
    const angle = n.depth === 0 ? 0 : WEDGE / 2 + n.x;
    return {
      id: data.checkpoint_id,
      parentId: data.parent_id,
      stepId: data.step_id,
      optionId: data.option_id,
      depth: n.depth,
      angle,
      radius,
      ...pointAt(angle, radius, aspect),
      isLeaf: !n.children || n.children.length === 0,
    };
  });
  return { nodes, ringGap, innerRadius, aspect, maxDepth, radiusOf };
}
