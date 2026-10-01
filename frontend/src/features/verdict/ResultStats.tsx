import type { AnalysisResult } from "../../shared/types/contracts";
import { formatNumber, formatP, formatSigned } from "./verdictFormat";

interface Props {
  result: AnalysisResult;
  tone: "gold" | "vermilion";
}

export function ResultStats({ result, tone }: Props) {
  return (
    <dl className={`vc-stats vc-stats--${tone}`}>
      <div>
        <dt>Estimate</dt>
        <dd className="mono vc-stats__estimate">{formatSigned(result.estimate)}</dd>
      </div>
      <div>
        <dt>95% CI</dt>
        <dd className="mono">
          [{formatNumber(result.ci_low)}, {formatNumber(result.ci_high)}]
        </dd>
      </div>
      <div>
        <dt>p</dt>
        <dd className="mono">{formatP(result.p_value)}</dd>
      </div>
    </dl>
  );
}
