import type { KeyboardEvent } from "react";
import type { Layout } from "./specCurveLayout";
import type { CurvePoint, MatrixRow } from "./specCurveData";

interface Props {
  point: CurvePoint;
  rows: readonly MatrixRow[];
  layout: Layout;
  x: number;
  selected: boolean;
  hovered: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}

export function UniverseColumn({ point, rows, layout, x, selected, hovered, onSelect, onHover }: Props) {
  const { y, step, top, curveHeight, matrixTop, rowHeight, height } = layout;
  const py = y(point.estimate);
  const onKey = (event: KeyboardEvent<SVGGElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(point.id);
    }
  };
  const radius = point.tone === "baseline" ? 6.5 : 4.5;

  return (
    <g
      className="sc-col"
      data-tone={point.tone}
      data-selected={selected}
      data-hovered={hovered}
      style={{ transform: `translate(${x}px, 0px)` }}
      role="button"
      tabIndex={0}
      aria-label={`Universe ${point.id}, estimate ${point.estimate.toFixed(3)}, ${point.verdict}`}
      aria-pressed={selected}
      onClick={() => onSelect(point.id)}
      onKeyDown={onKey}
      onMouseEnter={() => onHover(point.id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(point.id)}
      onBlur={() => onHover(null)}
    >
      <rect className="sc-col__band" x={-step / 2} y={top - 6} width={step} height={height - top} />
      <line className="sc-col__guide" y1={top} y2={top + curveHeight} />
      <line className="sc-whisker" y1={y(point.low)} y2={y(point.high)} />
      <line className="sc-cap" x1={-3} x2={3} y1={y(point.low)} y2={y(point.low)} />
      <line className="sc-cap" x1={-3} x2={3} y1={y(point.high)} y2={y(point.high)} />
      {point.tone === "baseline" && <circle className="sc-baseline-ring" cy={py} r={radius + 5} />}
      <circle className="sc-dot" cy={py} r={radius} />
      {rows.map((row, i) =>
        point.alternatives.has(row.stepId) ? (
          <circle key={row.stepId} className="sc-mdot" cy={matrixTop + i * rowHeight + rowHeight / 2} r={4} />
        ) : null,
      )}
    </g>
  );
}
