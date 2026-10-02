import type { AnalysisResult } from "../../shared/types/contracts";
import { formatNumber, formatP, formatEstimate } from "./verdictFormat";

interface Props {
  result: AnalysisResult;
  tone: "gold" | "vermilion";
  threshold: number;
}

export function ResultStats({ result, tone, threshold }: Props) {
  return (
    <dl className={`vc-stats vc-stats--${tone}`}>
      <div>
        <dt>Estimate</dt>
        <dd className="mono vc-stats__estimate">{formatEstimate(result.estimate, threshold)}</dd>
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
