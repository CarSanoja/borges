import { formatNumber, formatP } from "../verdict/verdictFormat";
import { titleFor, type CurvePoint, type MatrixRow } from "./specCurveData";

interface Props {
  point: CurvePoint;
  rows: readonly MatrixRow[];
  left: number;
  top: number;
  width: number;
}

export function SpecTooltip({ point, rows, left, top, width }: Props) {
  const clamped = Math.min(Math.max(left, 120), Math.max(120, width - 120));
  const changes = point.changed.length ? point.changed.map((id) => titleFor(rows, id)).join(" + ") : "Original path";
  return (
    <div className="sc-tip" role="tooltip" data-tone={point.tone} style={{ left: clamped, top }}>
      <span className="sc-tip__verdict">{point.verdict}</span>
      <span className="sc-tip__changes">{changes}</span>
      <span className="sc-tip__nums mono">
        {formatNumber(point.estimate)} [{formatNumber(point.low)}, {formatNumber(point.high)}] p {formatP(point.pValue)}
      </span>
    </div>
  );
}
