import { memo } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { TONE_VAR } from "./colors";
import type { Tone } from "./colors";
import { CENTER_RADIUS } from "./layout";
import type { GardenLayoutNode } from "./layout";

interface Props {
  node: GardenLayoutNode;
  tone: Tone | null;
  universeId: string | null;
  selected: boolean;
  onHover: (id: string, event: PointerEvent<SVGGElement>) => void;
  onLeave: () => void;
  onSelect: (universeId: string) => void;
}

function GardenNodeBase({ node, tone, universeId, selected, onHover, onLeave, onSelect }: Props) {
  const isUniverse = universeId !== null;
  const isRoot = node.depth === 0;
  const radius = isRoot ? CENTER_RADIUS : isUniverse ? (selected ? 9 : 7) : 4;
  const fill = tone ? TONE_VAR[tone] : "var(--paper-500)";
  const activate = () => {
    if (universeId) onSelect(universeId);
  };
  const onKey = (event: KeyboardEvent<SVGGElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate();
    }
  };
  return (
    <g transform={`translate(${node.x} ${node.y})`}>
      <g
        className={`garden-node${isUniverse ? " garden-node--leaf" : ""}${isRoot ? " garden-node--root" : ""}${selected ? " is-selected" : ""}`}
        data-testid="garden-node"
        data-node-id={node.id}
        data-leaf={isUniverse ? "true" : "false"}
        data-verdict={tone ?? "none"}
        role={isUniverse ? "button" : undefined}
        tabIndex={isUniverse ? 0 : undefined}
        aria-label={isUniverse ? `Universe ${universeId}` : undefined}
        aria-pressed={isUniverse ? selected : undefined}
        onPointerMove={(e) => onHover(node.id, e)}
        onPointerLeave={onLeave}
        onClick={activate}
        onKeyDown={onKey}
      >
        <circle r={radius + 8} className="garden-node-hit" />
        {selected && <circle r={radius + 5} className="garden-node-halo" style={{ stroke: fill }} />}
        <circle r={radius} className="garden-node-dot" style={{ fill }} />
      </g>
    </g>
  );
}

export const GardenNode = memo(GardenNodeBase);
