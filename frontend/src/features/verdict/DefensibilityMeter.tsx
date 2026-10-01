import { formatPercent } from "./verdictFormat";

interface Props {
  value: number | null;
}

export function DefensibilityMeter({ value }: Props) {
  if (value === null) {
    return <span className="vc-meter vc-meter--empty">Defensibility not scored</span>;
  }
  const share = Math.min(1, Math.max(0, value));
  return (
    <div className="vc-meter" role="meter" aria-label="Defensibility" aria-valuemin={0} aria-valuemax={1} aria-valuenow={share}>
      <span className="vc-meter__label">Defensibility</span>
      <span className="vc-meter__track" aria-hidden="true">
        <span className="vc-meter__fill" style={{ width: formatPercent(share) }} />
      </span>
      <span className="vc-meter__value mono">{formatPercent(share)}</span>
    </div>
  );
}
