import type { Universe } from "../../shared/types/contracts";
import { formatNumber, formatP } from "./labels";
import type { NodeLabel } from "./labels";
import { TONE_LABEL } from "./colors";
import type { Tone } from "./colors";

interface Props {
  x: number;
  y: number;
  label: NodeLabel;
  rows: number | null;
  universe: Universe | null;
  tone: Tone | null;
}

export function Tooltip({ x, y, label, rows, universe, tone }: Props) {
  const result = universe?.result ?? null;
  return (
    <div className="garden-tooltip" style={{ left: x, top: y }} role="tooltip" data-testid="garden-tooltip">
      <span className="eyebrow">{label.stepTitle}</span>
      <strong className="garden-tooltip-option">{label.optionLabel}</strong>
      {rows !== null && <span className="mono">{rows.toLocaleString("en-US")} rows</span>}
      {result && (
        <dl className="garden-tooltip-stats mono">
          <dt>estimate</dt>
          <dd>{formatNumber(result.estimate)}</dd>
          <dt>95% CI</dt>
          <dd>
            [{formatNumber(result.ci_low)}, {formatNumber(result.ci_high)}]
          </dd>
          <dt>p</dt>
          <dd>{formatP(result.p_value)}</dd>
        </dl>
      )}
      {universe && tone && (
        <span className={`garden-tooltip-verdict garden-tooltip-verdict--${tone}`}>
          {universe.verdict ?? TONE_LABEL[tone]}
        </span>
      )}
    </div>
  );
}
