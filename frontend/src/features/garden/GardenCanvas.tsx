import type { KeyboardEvent, PointerEvent } from "react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { GardenLink } from "./GardenLink";
import { GardenNode } from "./GardenNode";
import type { LinkRole } from "./GardenLink";
import { Rings } from "./Rings";
import { universeAriaLabel } from "./labels";
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

const noopFocus = () => undefined;

export function GardenCanvas({ snapshot, model, size, selectedUniverseId, interactive, showLabels, onHover, onLeave, onSelect }: Props) {
  const { plan } = snapshot;
  const leafIds = model.layout.nodes.filter((n) => model.leafUniverse.has(n.id)).map((n) => n.id);
  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    const current = (event.target as Element).closest("[data-node-id]")?.getAttribute("data-node-id") ?? null;
    const index = current ? leafIds.indexOf(current) : -1;
    if (index < 0) return;
    const last = leafIds.length - 1;
    const moves: Record<string, number> = {
      ArrowRight: Math.min(last, index + 1),
      ArrowDown: Math.min(last, index + 1),
      ArrowLeft: Math.max(0, index - 1),
      ArrowUp: Math.max(0, index - 1),
      Home: 0,
      End: last,
    };
    const target = moves[event.key];
    if (target === undefined) return;
    event.preventDefault();
    const id = leafIds[target] as string;
    event.currentTarget.querySelector<SVGGElement>(`[data-node-id="${id}"]`)?.focus();
  };
  const roleOf = new Map<string, LinkRole>(model.links.map((l) => [l.id, l.role]));
  return (
    <svg
      className="garden-svg"
      viewBox={`${-size.width / 2} ${-size.height / 2} ${size.width} ${size.height}`}
      role={interactive ? "group" : undefined}
      aria-label={interactive ? "Garden of forking analysis paths" : undefined}
      aria-hidden={interactive ? undefined : true}
      onKeyDown={interactive ? onKeyDown : undefined}
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
              ariaLabel={universe ? universeAriaLabel(plan, universe) : undefined}
              selected={universe !== undefined && universe.id === selectedUniverseId}
              tabbable
              interactive={interactive}
              onFocusNode={noopFocus}
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
