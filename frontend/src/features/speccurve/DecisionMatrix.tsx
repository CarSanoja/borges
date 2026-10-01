import type { Layout } from "./specCurveLayout";
import type { MatrixRow } from "./specCurveData";

interface Props {
  layout: Layout;
  rows: readonly MatrixRow[];
}

export function DecisionMatrix({ layout, rows }: Props) {
  const { matrixTop, rowHeight, left, width, right } = layout;
  return (
    <g className="sc-matrix">
      {rows.map((row, i) => {
        const cy = matrixTop + i * rowHeight + rowHeight / 2;
        return (
          <g key={row.stepId}>
            <line className="sc-matrix__rule" x1={left} x2={width - right} y1={cy} y2={cy} />
            <text className="sc-matrix__label" x={left - 10} y={cy} dy="0.32em" textAnchor="end">
              {row.title}
            </text>
          </g>
        );
      })}
    </g>
  );
}
