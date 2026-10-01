import type { Layout } from "./specCurveLayout";
import { formatNumber } from "../verdict/verdictFormat";

interface Props {
  layout: Layout;
  threshold: number | null;
}

export function CurveAxes({ layout, threshold }: Props) {
  const { y, left, width, right } = layout;
  const x2 = width - right;
  const ticks = y.ticks(5);
  const thresholdY = threshold === null ? null : y(threshold);
  return (
    <g className="sc-axes">
      {ticks.map((tick) => (
        <g key={tick} transform={`translate(0, ${y(tick)})`}>
          <line className="sc-grid" x1={left} x2={x2} />
          <text className="sc-tick" x={left - 10} dy="0.32em" textAnchor="end">
            {formatNumber(tick)}
          </text>
        </g>
      ))}
      {thresholdY !== null && (
        <g>
          <line className="sc-threshold" x1={left} x2={x2} y1={thresholdY} y2={thresholdY} />
          <text className="sc-threshold-label" x={x2} y={thresholdY - 5} textAnchor="end">
            decision threshold {formatNumber(threshold ?? 0)}
          </text>
        </g>
      )}
    </g>
  );
}
