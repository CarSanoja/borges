import type { Report } from "../../shared/types/contracts";
import type { EffectRange } from "./flipKind";
import { formatNumber, formatPercent } from "./verdictFormat";

interface Props {
  report: Report;
  range: EffectRange | null;
}

export function Robustness({ report, range }: Props) {
  const agree = Math.max(0, report.n_universes - report.n_flipped);
  const failed = report.n_failed ?? 0;
  return (
    <div className="vc-robust">
      <div className="vc-robust__head">
        <span className="eyebrow">Robustness</span>
        <span className="mono vc-robust__value">{formatPercent(report.robustness)}</span>
      </div>
      <span className="vc-robust__track" aria-hidden="true">
        <span className="vc-robust__fill" style={{ width: formatPercent(report.robustness) }} />
      </span>
      <p className="vc-robust__note">
        {agree} of {report.n_universes} explored universes agree
      </p>
      {range && (
        <p className="vc-robust__note vc-range">
          Effect range across {range.n} {range.n === 1 ? "universe" : "universes"}:{" "}
          <span className="mono">
            {formatNumber(range.min)} to {formatNumber(range.max)}
          </span>
        </p>
      )}
      {failed > 0 && (
        <p className="vc-robust__note vc-robust__note--warn" title={report.failed?.join("\n")}>
          {report.n_universes + failed} explored, {failed} could not run
        </p>
      )}
    </div>
  );
}
