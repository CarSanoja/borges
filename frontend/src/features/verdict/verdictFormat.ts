import type { DecisionRule } from "../../shared/types/contracts";

export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "n/a";
  const abs = Math.abs(value);
  if (abs === 0) return "0";
  if (abs < 0.01) return value.toPrecision(2);
  if (abs >= 100) return value.toFixed(1);
  if (abs >= 10) return value.toFixed(2);
  return value.toFixed(3);
}

export function formatEstimate(value: number, threshold: number): string {
  const text = formatNumber(value);
  return value > 0 && threshold === 0 ? `+${text}` : text;
}

export function formatP(value: number): string {
  if (!Number.isFinite(value)) return "n/a";
  return value < 0.001 ? "< 0.001" : value.toFixed(3);
}

export function formatPercent(share: number): string {
  return `${Math.round(share * 100)}%`;
}

export function ruleInWords(rule: DecisionRule): string {
  const direction = rule.comparator === "gt" ? "above" : "below";
  return `Decide "${rule.positive_label}" when ${rule.metric} is ${direction} ${rule.threshold} and p is under ${rule.alpha}; otherwise "${rule.negative_label}".`;
}
