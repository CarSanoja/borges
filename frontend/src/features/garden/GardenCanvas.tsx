import type { PointerEvent } from "react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { GardenLink } from "./GardenLink";
import { GardenNode } from "./GardenNode";
import type { LinkRole } from "./GardenLink";
import { Rings } from "./Rings";
import { RootLabel } from "./RootLabel";
import type { ElementSize } from "./useElementSize";
import type { GardenModel } from "./useGardenModel";

interface Props {
  snapshot: RunSnapshot;
  model: GardenModel;
  size: ElementSize;
  selectedUniverseId: string | null;
  interactive: boolean;
  showLabels: boolean;
  onHover: (id: string, event: PointerEvent<SVGGElement>) => void;
  onLeave: () => void;
  onSelect: (id: string) => void;
}

export function GardenCanvas({ snapshot, model, size, selectedUniverseId, interactive, showLabels, onHover, onLeave, onSelect }: Props) {
  const { plan } = snapshot;
  const roleOf = new Map<string, LinkRole>(model.links.map((l) => [l.id, l.role]));
  return (
    <svg
      className="garden-svg"
      viewBox={`${-size.width / 2} ${-size.height / 2} ${size.width} ${size.height}`}
      role={interactive ? "group" : undefined}
      aria-label={interactive ? "Garden of forking analysis paths" : undefined}
      aria-hidden={interactive ? undefined : true}
    >
      {plan && <Rings steps={plan.steps} radiusOf={model.layout.radiusOf} aspect={model.layout.aspect} showLabels={showLabels} />}
      <g>
        {model.links.map((l) => (
          <GardenLink key={l.id} parent={l.parent} child={l.child} role={l.role} aspect={model.layout.aspect} />
        ))}
      </g>
      <g>
        {model.layout.nodes.map((node) => {
          const universe = model.leafUniverse.get(node.id);
          return (
            <GardenNode
              key={node.id}
              node={node}
              tone={model.leafTone.get(node.id) ?? null}
              role={roleOf.get(node.id) ?? "baseline"}
              universeId={universe?.id ?? null}
              selected={universe !== undefined && universe.id === selectedUniverseId}
              interactive={interactive}
              onHover={onHover}
              onLeave={onLeave}
              onSelect={onSelect}
            />
          );
        })}
      </g>
      <RootLabel dataset={plan?.dataset} />
    </svg>
  );
}
