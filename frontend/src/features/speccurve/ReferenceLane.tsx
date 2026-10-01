import type { ReferenceEstimate } from "../../shared/types/contracts";
import { formatNumber } from "../verdict/verdictFormat";
import type { Layout } from "./specCurveLayout";

interface Props {
  layout: Layout;
  reference: readonly ReferenceEstimate[];
  label: string;
}

export function ReferenceLane({ layout, reference, label }: Props) {
  const { y, width, right, top, curveHeight } = layout;
  const x0 = width - right + 14;
  const center = x0 + 30;
  return (
    <g className="sc-reference" aria-label={label}>
      <line className="sc-reference__rail" x1={x0 - 6} x2={x0 - 6} y1={top} y2={top + curveHeight} />
      <text className="sc-reference__label" x={center} y={top + curveHeight + 16} textAnchor="middle">
        {label}
      </text>
      {reference.map((r, i) => {
        const jitter = ((i % 5) - 2) * 4;
        const cx = center + jitter;
        const py = y(r.estimate);
        return (
          <g key={`${r.label}-${i}`} data-significant={r.significant === null ? "unknown" : String(r.significant)}>
            <title>{`${r.label}: ${formatNumber(r.estimate)}`}</title>
            {r.ci_low !== null && r.ci_high !== null && (
              <line className="sc-reference__ci" x1={cx} x2={cx} y1={y(r.ci_low)} y2={y(r.ci_high)} />
            )}
            <line className="sc-reference__tick" x1={cx - 9} x2={cx + 9} y1={py} y2={py} />
          </g>
        );
      })}
    </g>
  );
}
