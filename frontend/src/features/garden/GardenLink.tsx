import { memo } from "react";
import { linkRadial } from "d3-shape";
import type { GardenLayoutNode } from "./layout";

export type LinkRole = "plain" | "baseline" | "flip" | "selected";

interface Props {
  parent: GardenLayoutNode;
  child: GardenLayoutNode;
  role: LinkRole;
}

const radialLink = linkRadial<{ source: GardenLayoutNode; target: GardenLayoutNode }, GardenLayoutNode>()
  .angle((n) => n.angle)
  .radius((n) => n.radius);

function GardenLinkBase({ parent, child, role }: Props) {
  const d = radialLink({ source: parent, target: child }) ?? "";
  return (
    <path
      d={d}
      pathLength={1}
      className={`garden-link garden-link--${role}`}
      data-testid="garden-link"
      data-role={role}
    />
  );
}

export const GardenLink = memo(GardenLinkBase);
