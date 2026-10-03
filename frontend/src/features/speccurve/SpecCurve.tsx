import { useMemo, useState } from "react";
import type { KeyboardEvent } from "react";
import type { ReferenceEstimate, RunSnapshot } from "../../shared/types/contracts";
import { CurveAxes } from "./CurveAxes";
import { DecisionMatrix } from "./DecisionMatrix";
import { ReferenceLane } from "./ReferenceLane";
import { SpecTooltip } from "./SpecTooltip";
import { UniverseColumn } from "./UniverseColumn";
import { buildPoints, buildRows, yDomain } from "./specCurveData";
import { columnX, makeLayout } from "./specCurveLayout";
import { useElementWidth } from "./useElementWidth";
import "./speccurve.css";
import "./specCurveTooltip.css";

interface Props {
  snapshot: RunSnapshot;
  reference?: ReferenceEstimate[];
  referenceLabel?: string | null;
  selectedUniverseId: string | null;
  onSelectUniverse: (id: string) => void;
}

const NO_REFERENCE: ReferenceEstimate[] = [];

export function SpecCurve({ snapshot, reference, referenceLabel, selectedUniverseId, onSelectUniverse }: Props) {
  const [ref, width] = useElementWidth();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const refs = reference ?? NO_REFERENCE;
  const threshold = (snapshot.decision_rule ?? snapshot.plan?.decision_rule)?.threshold ?? null;
  const yLabel = (snapshot.decision_rule ?? snapshot.plan?.decision_rule)?.metric ?? "estimate";
  const points = useMemo(() => buildPoints(snapshot), [snapshot]);
  const rows = useMemo(() => buildRows(snapshot, points), [snapshot, points]);
  const layout = useMemo(
    () => makeLayout(width, rows.length, points.length, refs.length > 0, yDomain(points, threshold, refs)),
    [width, rows.length, points, refs, threshold],
  );
  const markers = useMemo(
    () =>
      points.map((point, i) => ({
        x: columnX(layout, i),
        yTop: Math.min(layout.y(point.high), layout.y(point.low), layout.y(point.estimate)),
        yBottom: Math.max(layout.y(point.high), layout.y(point.low), layout.y(point.estimate)),
      })),
    [points, layout],
  );
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const stopId = [focusedId, selectedUniverseId].find((id) => id && points.some((p) => p.id === id)) ?? points[0]?.id ?? null;
  const onKeyDown = (event: KeyboardEvent<SVGSVGElement>) => {
    const current = (event.target as Element).closest("[data-universe-id]")?.getAttribute("data-universe-id");
    const index = points.findIndex((p) => p.id === current);
    if (index < 0) return;
    const last = points.length - 1;
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
    const id = (points[target] as { id: string }).id;
    setFocusedId(id);
    event.currentTarget.querySelector<SVGGElement>(`[data-universe-id="${id}"]`)?.focus();
  };
  const hoverIndex = points.findIndex((p) => p.id === hoveredId);
  const hovered = hoverIndex >= 0 ? points[hoverIndex] : undefined;

  return (
    <section className="panel sc" aria-label="Specification curve">
      <header className="sc-head">
        <span className="eyebrow">Specification curve</span>
        <ul className="sc-legend">
          <li data-tone="baseline">original path</li>
          <li data-tone="agree">agrees</li>
          <li data-tone="flip">flips</li>
        </ul>
        <span className="sc-count mono">{points.length} {points.length === 1 ? "universe" : "universes"}</span>
      </header>
      <div className="sc-body" ref={ref}>
        {points.length === 0 ? (
          <p className="sc-empty">Finished universes appear here, sorted by estimate.</p>
        ) : (
          <svg width={width} height={layout.height} role="group" aria-label="Estimates by universe" onKeyDown={onKeyDown}>
            <CurveAxes layout={layout} threshold={threshold} yLabel={yLabel} markers={markers} />
            <DecisionMatrix layout={layout} rows={rows} />
            {refs.length > 0 && <ReferenceLane layout={layout} reference={refs} label={referenceLabel ?? "Reference"} />}
            {points.map((point, i) => (
              <UniverseColumn
                key={point.id}
                point={point}
                rows={rows}
                layout={layout}
                x={columnX(layout, i)}
                selected={point.id === selectedUniverseId}
                tabbable={point.id === stopId}
                hovered={point.id === hoveredId}
                onSelect={onSelectUniverse}
                onHover={(id) => {
                  setHoveredId(id);
                  if (id) setFocusedId(id);
                }}
              />
            ))}
          </svg>
        )}
        {hovered && (
          <SpecTooltip
            point={hovered}
            rows={rows}
            left={columnX(layout, hoverIndex)}
            top={layout.y(hovered.estimate)}
            width={width}
          />
        )}
      </div>
    </section>
  );
}
