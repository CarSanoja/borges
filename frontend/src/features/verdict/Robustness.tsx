import type { Report } from "../../shared/types/contracts";
import type { EffectRange } from "./flipKind";
import { formatNumber, formatPercent } from "./verdictFormat";

interface Props {
  report: Report;
  range: EffectRange | null;
}

interface RatedProps {
  report: Report;
  range: EffectRange | null;
  agree: number;
  failed: number;
}

function TooFewToRate({ report, range, agree, failed }: RatedProps) {
  return (
    <div className="vc-robust" data-testid="robustness-unrated">
      <div className="vc-robust__head">
        <span className="eyebrow">Robustness</span>
        <span className="mono vc-robust__value vc-robust__value--unrated">n={report.n_universes}, too few to rate</span>
      </div>
      <p className="vc-robust__note">
        {agree} of {report.n_universes} paths agree with the baseline
      </p>
      {report.robustness_rating_reason && <p className="vc-robust__note">{report.robustness_rating_reason}</p>}
      {range && (
        <p className="vc-robust__note vc-range">
          Effect range across {range.n} {range.n === 1 ? "universe" : "universes"}:{" "}
          <span className="mono">
            {formatNumber(range.min)} to {formatNumber(range.max)}
          </span>
        </p>
      )}
      {failed > 0 && (
        <p className="vc-robust__note vc-robust__note--warn">
          {report.n_universes + failed} explored, {failed} could not run
        </p>
      )}
    </div>
  );
}

export function Robustness({ report, range }: Props) {
  const agree = Math.max(0, report.n_universes - report.n_flipped);
  const failed = report.n_failed ?? 0;
  if (report.robustness_rating === null) return <TooFewToRate report={report} range={range} agree={agree} failed={failed} />;
  const shown = report.robustness_rating ?? report.robustness;
  return (
    <div className="vc-robust">
      <div className="vc-robust__head">
        <span className="eyebrow">Robustness</span>
        <span className="mono vc-robust__value">{formatPercent(shown)}</span>
      </div>
      <span className="vc-robust__track" aria-hidden="true">
        <span className="vc-robust__fill" style={{ width: formatPercent(shown) }} />
      </span>
      <p className="vc-robust__note">
        {agree} of {report.n_universes} paths agree with the baseline
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
