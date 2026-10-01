import { useCallback, useRef, useState } from "react";
import type { PointerEvent } from "react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { GardenLink } from "./GardenLink";
import { GardenNode } from "./GardenNode";
import { Legend } from "./Legend";
import { Rings } from "./Rings";
import { Tooltip } from "./Tooltip";
import { resolveLabel } from "./labels";
import { VIEW_RADIUS } from "./layout";
import { useGardenModel } from "./useGardenModel";
import "./garden.css";

interface Props {
  snapshot: RunSnapshot;
  selectedUniverseId: string | null;
  onSelectUniverse: (id: string) => void;
}

interface Hover {
  id: string;
  x: number;
  y: number;
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function Garden({ snapshot, selectedUniverseId, onSelectUniverse }: Props) {
  const model = useGardenModel(snapshot, selectedUniverseId);
  const frame = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const { plan } = snapshot;

  const onHover = useCallback((id: string, event: PointerEvent<SVGGElement>) => {
    const rect = frame.current?.getBoundingClientRect();
    if (!rect) return;
    setHover({ id, x: event.clientX - rect.left, y: event.clientY - rect.top });
  }, []);
  const onLeave = useCallback(() => setHover(null), []);

  if (model.layout.nodes.length === 0) {
    return (
      <div className="panel garden garden--empty" data-testid="garden-empty">
        <span className="eyebrow">Garden</span>
        <p className="garden-empty-text">The garden has not been planted yet.</p>
      </div>
    );
  }

  const hovered = hover ? model.byId.get(hover.id) : undefined;
  const hoveredUniverse = hover ? (model.leafUniverse.get(hover.id) ?? null) : null;
  const dataset = plan?.dataset;
  const flipId = snapshot.flip?.universe_id ?? null;

  return (
    <div
      className={`panel garden${selectedUniverseId ? " has-selection" : ""}${flipId ? " has-flip" : ""}`}
      ref={frame}
    >
      <span className="eyebrow garden-eyebrow">Garden of forking paths</span>
      <svg
        className="garden-svg"
        viewBox={`${-VIEW_RADIUS} ${-VIEW_RADIUS} ${VIEW_RADIUS * 2} ${VIEW_RADIUS * 2}`}
        role="group"
        aria-label="Garden of forking analysis paths"
      >
        {plan && <Rings steps={plan.steps} ringGap={model.layout.ringGap} />}
        <g>
          {model.links.map((l) => (
            <GardenLink key={l.id} parent={l.parent} child={l.child} role={l.role} />
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
                universeId={universe?.id ?? null}
                selected={universe !== undefined && universe.id === selectedUniverseId}
                onHover={onHover}
                onLeave={onLeave}
                onSelect={onSelectUniverse}
              />
            );
          })}
        </g>
        <g className="garden-core-label" aria-hidden="true">
          <text y={-3}>{truncate(dataset?.name ?? "dataset", 14)}</text>
          <text y={11} className="mono">
            {dataset ? `${dataset.n_rows.toLocaleString("en-US")} rows` : ""}
          </text>
        </g>
      </svg>
      <Legend />
      {hover && hovered && (
        <Tooltip
          x={hover.x}
          y={hover.y}
          label={resolveLabel(plan, {
            step_id: hovered.stepId,
            option_id: hovered.optionId,
          })}
          rows={hovered.depth === 0 ? (dataset?.n_rows ?? null) : null}
          universe={hoveredUniverse}
          tone={model.leafTone.get(hover.id) ?? null}
        />
      )}
    </div>
  );
}
