import type { Layout } from "./specCurveLayout";
import { joinableLines, wrapLabel } from "./wrapLabel";
import { formatNumber } from "../verdict/verdictFormat";
import { placeThresholdLabel, type Marker } from "./thresholdLabel";

interface Props {
  layout: Layout;
  threshold: number | null;
  yLabel: string;
  markers?: readonly Marker[];
}

export function CurveAxes({ layout, threshold, yLabel, markers = [] }: Props) {
  const { y, left, width, right, top, curveHeight } = layout;
  const x2 = width - right;
  const ticks = y.ticks(5);
  const lines = joinableLines(wrapLabel(yLabel, Math.floor(curveHeight / 6.4)));
  const lineHeight = 13;
  const thresholdY = threshold === null ? null : y(threshold);
  const thresholdText = `decision threshold ${formatNumber(threshold ?? 0)}`;
  const spot = thresholdY === null ? null : placeThresholdLabel(markers, thresholdY, thresholdText, left, x2);
  return (
    <g className="sc-axes">
      <text
        className="sc-axis-label"
        transform={`translate(12, ${top + curveHeight / 2}) rotate(-90)`}
        textAnchor="middle"
      >
        <title>{yLabel}</title>
        {lines.map((line, index) => (
          <tspan key={index} x={0} dy={index === 0 ? 0 : lineHeight}>
            {line}
          </tspan>
        ))}
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
          <text
            className="sc-threshold-label"
            x={spot?.x ?? left - 10}
            y={spot?.y ?? thresholdY - 6}
            textAnchor={spot?.anchor ?? "end"}
          >
            {spot ? thresholdText : `threshold ${formatNumber(threshold ?? 0)}`}
          </text>
        </g>
      )}
    </g>
  );
}
