import { useMemo, useState } from "react";
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
  const points = useMemo(() => buildPoints(snapshot), [snapshot]);
  const rows = useMemo(() => buildRows(snapshot, points), [snapshot, points]);
  const layout = useMemo(
    () => makeLayout(width, rows.length, points.length, refs.length > 0, yDomain(points, threshold, refs)),
    [width, rows.length, points, refs, threshold],
  );
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
        <span className="sc-count mono">{points.length} universes</span>
      </header>
      <div className="sc-body" ref={ref}>
        {points.length === 0 ? (
          <p className="sc-empty">Finished universes appear here, sorted by estimate.</p>
        ) : (
          <svg width={width} height={layout.height} role="group" aria-label="Estimates by universe">
            <CurveAxes layout={layout} threshold={threshold} />
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
                hovered={point.id === hoveredId}
                onSelect={onSelectUniverse}
                onHover={setHoveredId}
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
