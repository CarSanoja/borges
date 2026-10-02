import { memo } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { TONE_VAR } from "./colors";
import type { Tone } from "./colors";
import type { LinkRole } from "./GardenLink";
import { ROOT_RADIUS } from "./layout";
import type { GardenLayoutNode } from "./layout";

interface Props {
  node: GardenLayoutNode;
  tone: Tone | null;
  role: LinkRole;
  universeId: string | null;
  ariaLabel?: string;
  selected: boolean;
  interactive: boolean;
  onHover: (id: string, event: PointerEvent<SVGGElement>) => void;
  onLeave: () => void;
  onSelect: (universeId: string) => void;
}

const ROLE_FILL: Record<LinkRole, string> = {
  plain: "var(--paper-500)",
  baseline: "var(--gold)",
  flip: "var(--vermilion)",
  selected: "var(--paper-100)",
};

function nodeRadius(isRoot: boolean, isUniverse: boolean, selected: boolean, role: LinkRole): number {
  if (isRoot) return ROOT_RADIUS;
  if (isUniverse) return selected ? 9 : role === "flip" ? 8.5 : 7;
  return 4.5;
}

function GardenNodeBase({ node, tone, role, universeId, ariaLabel, selected, interactive, onHover, onLeave, onSelect }: Props) {
  const isUniverse = universeId !== null;
  const isRoot = node.depth === 0;
  const radius = nodeRadius(isRoot, isUniverse, selected, role);
  const fill = isRoot ? "var(--ink-800)" : isUniverse && tone ? TONE_VAR[tone] : ROLE_FILL[role];
  const activate = () => {
    if (universeId) onSelect(universeId);
  };
  const onKey = (event: KeyboardEvent<SVGGElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate();
    }
  };
  const live = interactive && isUniverse;
  const classes = [
    "garden-node",
    isUniverse ? "garden-node--leaf" : "",
    isRoot ? "garden-node--root" : "",
    selected ? "is-selected" : "",
    role === "flip" && isUniverse ? "garden-node--flip" : "",
  ];
  return (
    <g transform={`translate(${node.x} ${node.y})`} className={`garden-wrap garden-wrap--${role}`}>
      <g
        className={classes.filter(Boolean).join(" ")}
        data-testid="garden-node"
        data-node-id={node.id}
        data-leaf={isUniverse ? "true" : "false"}
        data-verdict={tone ?? "none"}
        role={live ? "button" : undefined}
        tabIndex={live ? 0 : undefined}
        aria-label={live ? (ariaLabel ?? `Universe ${universeId}`) : undefined}
        aria-pressed={live ? selected : undefined}
        onPointerMove={interactive ? (e) => onHover(node.id, e) : undefined}
        onPointerLeave={interactive ? onLeave : undefined}
        onClick={live ? activate : undefined}
        onKeyDown={live ? onKey : undefined}
      >
        {interactive && <circle r={radius + 8} className="garden-node-hit" />}
        {isRoot && <circle r={radius + 7} className="garden-node-root-ring" />}
        {isUniverse && <circle r={radius + 5} className="garden-node-glow" style={{ fill }} />}
        {selected && <circle r={radius + 5} className="garden-node-halo" style={{ stroke: fill }} />}
        <circle r={radius} className="garden-node-dot" style={{ fill, color: fill }} />
      </g>
    </g>
  );
}

export const GardenNode = memo(GardenNodeBase);
