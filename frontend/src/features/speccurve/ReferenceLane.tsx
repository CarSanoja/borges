import type { ReferenceEstimate } from "../../shared/types/contracts";
import { formatNumber } from "../verdict/verdictFormat";
import type { Layout } from "./specCurveLayout";
import "./referenceLane.css";

interface Props {
  layout: Layout;
  reference: readonly ReferenceEstimate[];
  label: string;
}

export function ReferenceLane({ layout, reference, label }: Props) {
  const { y, width, right, top, curveHeight } = layout;
  if (reference.length === 0) return null;
  const x0 = width - right + 14;
  const center = x0 + 22;
  const estimates = reference.map((r) => r.estimate);
  const low = Math.min(...estimates);
  const high = Math.max(...estimates);
  return (
    <g className="sc-reference" aria-label={label}>
      <line className="sc-reference__rail" x1={x0 - 6} x2={x0 - 6} y1={top} y2={top + curveHeight} />
      <line className="sc-reference__range" x1={x0 + 4} x2={x0 + 4} y1={y(low)} y2={y(high)} />
      <text className="sc-reference__value" x={center + 16} y={y(high)} dy="0.32em">
        {formatNumber(high)}
      </text>
      <text className="sc-reference__value" x={center + 16} y={y(low)} dy="0.32em">
        {formatNumber(low)}
      </text>
      <text className="sc-reference__label" x={width} y={top + curveHeight + 18} textAnchor="end">
        {label}
      </text>
      {reference.map((r, i) => (
        <line
          key={`${r.label}-${i}`}
          className="sc-reference__tick"
          data-significant={r.significant === null ? "unknown" : String(r.significant)}
          x1={center - 10}
          x2={center + 10}
          y1={y(r.estimate)}
          y2={y(r.estimate)}
        >
          <title>{`${r.label}: ${formatNumber(r.estimate)}`}</title>
        </line>
      ))}
    </g>
  );
}
