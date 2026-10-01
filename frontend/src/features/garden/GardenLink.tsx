import { memo } from "react";
import { pointAt } from "./layout";
import type { GardenLayoutNode } from "./layout";

export type LinkRole = "plain" | "baseline" | "flip" | "selected";

interface Props {
  parent: GardenLayoutNode;
  child: GardenLayoutNode;
  role: LinkRole;
  aspect: number;
}

export function linkPath(parent: GardenLayoutNode, child: GardenLayoutNode, aspect: number): string {
  const mid = (parent.radius + child.radius) / 2;
  const a = pointAt(parent.angle, parent.radius, aspect);
  const b = pointAt(parent.angle, mid, aspect);
  const c = pointAt(child.angle, mid, aspect);
  const d = pointAt(child.angle, child.radius, aspect);
  return `M${a.x},${a.y}C${b.x},${b.y} ${c.x},${c.y} ${d.x},${d.y}`;
}

function GardenLinkBase({ parent, child, role, aspect }: Props) {
  return (
    <path
      d={linkPath(parent, child, aspect)}
      pathLength={1}
      className={`garden-link garden-link--${role}`}
      data-testid="garden-link"
      data-role={role}
    />
  );
}

export const GardenLink = memo(GardenLinkBase);
