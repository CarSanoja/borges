import type { DecisionRule } from "../../shared/types/contracts";

export function describeRule(rule: DecisionRule): string {
  const direction = rule.comparator === "gt" ? "above" : "below";
  return `${rule.positive_label} when ${rule.metric} is ${direction} ${rule.threshold} at p < ${rule.alpha}; otherwise ${rule.negative_label}.`;
}
