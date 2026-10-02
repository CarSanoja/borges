import type { Layout } from "./specCurveLayout";
import { formatNumber } from "../verdict/verdictFormat";

interface Props {
  layout: Layout;
  threshold: number | null;
  yLabel: string;
}

export function CurveAxes({ layout, threshold, yLabel }: Props) {
  const { y, left, width, right, top, curveHeight } = layout;
  const x2 = width - right;
  const ticks = y.ticks(5);
  const thresholdY = threshold === null ? null : y(threshold);
  return (
    <g className="sc-axes">
      <text
        className="sc-axis-label"
        transform={`translate(12, ${top + curveHeight / 2}) rotate(-90)`}
        textAnchor="middle"
      >
        {yLabel.length > 34 ? `${yLabel.slice(0, 33)}…` : yLabel}
      </text>
      <text className="sc-axis-label" x={x2} y={top + curveHeight + 20} textAnchor="end">
        universes, sorted by estimate
      </text>
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
          <text className="sc-threshold-label" x={left + 6} y={thresholdY + 14} textAnchor="start">
            decision threshold {formatNumber(threshold ?? 0)}
          </text>
        </g>
      )}
    </g>
  );
}
