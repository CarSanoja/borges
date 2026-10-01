import { stratify, tree } from "d3-hierarchy";
import type { CheckpointNode } from "../../shared/types/contracts";

export const VIEW_RADIUS = 440;
export const CENTER_RADIUS = 34;
const OUTER_PADDING = 56;

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
  maxDepth: number;
}

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

export function pointAt(angle: number, radius: number): { x: number; y: number } {
  return { x: radius * Math.sin(angle), y: -radius * Math.cos(angle) };
}

export function computeLayout(checkpoints: CheckpointNode[], stepCount: number): GardenLayout {
  const kept = reachableCheckpoints(checkpoints);
  if (kept.length === 0) return { nodes: [], ringGap: 0, maxDepth: 0 };
  const root = stratify<CheckpointNode>()
    .id((d) => d.checkpoint_id)
    .parentId((d) => d.parent_id)(kept);
  const maxDepth = root.height;
  const ringGap = (VIEW_RADIUS - OUTER_PADDING) / Math.max(stepCount, maxDepth, 1);
  const leafCount = Math.max(root.leaves().length, 1);
  const laidOut = tree<CheckpointNode>()
    .size([2 * Math.PI * (leafCount / (leafCount + 1)), 1])
    .separation((a, b) => (a.parent === b.parent ? 1 : 1.5) / Math.max(a.depth, 1))(root);
  const nodes: GardenLayoutNode[] = laidOut.descendants().map((n) => {
    const data = n.data;
    const radius = n.depth * ringGap;
    const angle = n.depth === 0 ? 0 : n.x;
    return {
      id: data.checkpoint_id,
      parentId: data.parent_id,
      stepId: data.step_id,
      optionId: data.option_id,
      depth: n.depth,
      angle,
      radius,
      ...pointAt(angle, radius),
      isLeaf: !n.children || n.children.length === 0,
    };
  });
  return { nodes, ringGap, maxDepth };
}
