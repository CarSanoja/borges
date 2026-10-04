import { useCallback, useEffect, useRef, useState } from "react";
import type { PointerEvent } from "react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { statusLabel } from "../run/runLabels";
import { GardenCanvas } from "./GardenCanvas";
import { Legend } from "./Legend";
import { Tooltip } from "./Tooltip";
import { UniverseList } from "./UniverseList";
import { resolveLabel } from "./labels";
import { useElementSize } from "./useElementSize";
import { useGardenModel } from "./useGardenModel";
import { useSpotlight } from "./useSpotlight";
import "./garden.css";
import "./gardenMarks.css";
import "./gardenMotion.css";

interface Props {
  snapshot: RunSnapshot;
  selectedUniverseId?: string | null;
  onSelectUniverse?: (id: string) => void;
  ambient?: boolean;
}

const RING_MARGIN = 26;
const MAX_ASPECT = 1.7;

interface Hover {
  id: string;
  x: number;
  y: number;
}

export function Garden({ snapshot, selectedUniverseId = null, onSelectUniverse, ambient = false }: Props) {
  const interactive = !ambient;
  const frame = useRef<HTMLDivElement>(null);
  const [stageRef, size] = useElementSize();
  const outerRadius = Math.max(60, Math.min(size.height, size.width) / 2 - RING_MARGIN);
  const aspect = Math.min(MAX_ASPECT, Math.max(1, (size.width / 2 - RING_MARGIN) / outerRadius));
  const model = useGardenModel(snapshot, selectedUniverseId, outerRadius, aspect);
  const [hover, setHover] = useState<Hover | null>(null);
  const flipId = snapshot.flip?.universe_id ?? null;
  const spotlight = useSpotlight(flipId);
  const { plan } = snapshot;

  const onHover = useCallback((id: string, event: PointerEvent<SVGGElement>) => {
    const rect = frame.current?.getBoundingClientRect();
    if (!rect) return;
    setHover({ id, x: event.clientX - rect.left, y: event.clientY - rect.top });
  }, []);
  const onLeave = useCallback(() => setHover(null), []);
  const hoverActive = hover !== null;

  useEffect(() => {
    setHover(null);
  }, [selectedUniverseId]);

  useEffect(() => {
    if (!hoverActive) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setHover(null);
    };
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [hoverActive]);
  const onSelect = useCallback((id: string) => onSelectUniverse?.(id), [onSelectUniverse]);

  const planted = model.layout.nodes.length > 0;
  const active = snapshot.status === "running" || snapshot.status === "queued";
  if (!planted && ambient) return <div className="garden garden--ambient" aria-hidden="true" />;
  if (!planted) {
    return (
      <div className="panel garden garden--empty" data-testid="garden-empty">
        <span className="eyebrow">Garden</span>
        <p className="garden-empty-text">
          {active ? `${statusLabel(snapshot)}. The garden appears once the plan is ready.` : "The garden has not been planted yet."}
        </p>
      </div>
    );
  }

  const hovered = hover ? model.byId.get(hover.id) : undefined;
  const hoveredUniverse = hover ? (model.leafUniverse.get(hover.id) ?? null) : null;
  const classes = [
    ambient ? "garden garden--ambient" : "panel garden",
    selectedUniverseId ? "has-selection" : "",
    flipId ? "has-flip" : "",
    spotlight ? "is-spotlight" : "",
  ];

  return (
    <div className={classes.filter(Boolean).join(" ")} ref={frame} aria-hidden={ambient ? true : undefined}>
      {interactive && <span className="eyebrow garden-eyebrow">Garden of forking paths</span>}
      <div className="garden-stage" ref={stageRef}>
        <GardenCanvas
          snapshot={snapshot}
          model={model}
          size={size}
          selectedUniverseId={selectedUniverseId}
          interactive={interactive}
          showLabels={interactive}
          onHover={onHover}
          onLeave={onLeave}
          onSelect={onSelect}
        />
      </div>
      {interactive && <UniverseList plan={plan} universes={Object.values(snapshot.garden.universes)} onSelect={onSelect} />}
      {interactive && <Legend />}
      {interactive && hover && hovered && (
        <Tooltip
          x={hover.x}
          y={hover.y}
          label={resolveLabel(plan, { step_id: hovered.stepId, option_id: hovered.optionId })}
          rows={hovered.depth === 0 ? (plan?.dataset.n_rows ?? null) : null}
          universe={hoveredUniverse}
          tone={model.leafTone.get(hover.id) ?? null}
        />
      )}
    </div>
  );
}
