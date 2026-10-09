import type { AnalysisPlan, Report } from "../../shared/types/contracts";
import { withPlanLabels } from "../run/planLabels";
import type { EffectRange } from "./flipKind";
import { formatNumber, formatPercent } from "./verdictFormat";

interface Props {
  report: Report;
  range: EffectRange | null;
  plan?: AnalysisPlan | null;
  inconclusive?: boolean;
}

function Interval({ report }: { report: Report }) {
  if (report.robustness_low == null || report.robustness_high == null) return null;
  return (
    <p className="vc-robust__interval" data-testid="robustness-interval">
      Sampled from the grid: 95% interval{" "}
      <span className="mono">
        {formatPercent(report.robustness_low)} to {formatPercent(report.robustness_high)}
      </span>
    </p>
  );
}

function Secondary({ report, range, plan }: Props) {
  const failed = report.n_failed ?? 0;
  const reason = report.robustness_rating === null ? report.robustness_rating_reason : null;
  return (
    <div className="vc-robust__secondary">
      <Interval report={report} />
      {reason && <p>{withPlanLabels(reason, plan)}</p>}
      {range && (
        <p className="vc-range">
          Effect range across {range.n} {range.n === 1 ? "universe" : "universes"}:{" "}
          <span className="mono">
            {formatNumber(range.min)} to {formatNumber(range.max)}
          </span>
        </p>
      )}
      {failed > 0 && (
        <p className="vc-robust__note--warn" title={report.failed?.join("\n")}>
          {report.n_universes + failed} explored, {failed} could not run
        </p>
      )}
    </div>
  );
}

export function Robustness({ report, range, plan = null, inconclusive = false }: Props) {
  const total = report.n_universes;
  if (report.robustness_rating === null) {
    return (
      <div className="vc-robust" data-testid="robustness-unrated">
        <span className="eyebrow">Robustness</span>
        <p className="vc-robust__headline">
          Too few distinct paths ({total}) to rate robustness
        </p>
        <Secondary report={report} range={range} plan={plan} />
      </div>
    );
  }
  const shown = report.robustness_rating ?? report.robustness;
  return (
    <div className="vc-robust" data-inconclusive={inconclusive}>
      <div className="vc-robust__head">
        <span className="eyebrow">Robustness</span>
        <span className="mono vc-robust__value">{formatPercent(shown)}</span>
      </div>
      <span className="vc-robust__track" aria-hidden="true">
        <span className="vc-robust__fill" style={{ width: formatPercent(shown) }} />
      </span>
      <Secondary report={report} range={range} plan={plan} />
    </div>
  );
}
