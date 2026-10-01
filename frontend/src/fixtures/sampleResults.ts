import type { AnalysisResult, DecisionRule } from "../shared/types/contracts";

interface Row {
  estimate: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
}

export const BASE_ROWS = 48210;

export const ROW_FACTORS: Record<string, number> = {
  exclude_internal: 0.974,
  min_2s: 0.962,
  adv_min_5s: 0.931,
  drop_first_3_days: 0.92,
  first_session_per_user: 0.71,
};

const OVERRIDES: Record<string, Row> = {
  baseline: { estimate: 0.62, ci_low: 0.18, ci_high: 1.06, p_value: 0.006 },
  exclude_internal: { estimate: 0.04, ci_low: -0.4, ci_high: 0.48, p_value: 0.86 },
  min_2s: { estimate: 0.58, ci_low: 0.13, ci_high: 1.03, p_value: 0.011 },
  adv_min_5s: { estimate: 0.55, ci_low: 0.1, ci_high: 1.0, p_value: 0.016 },
  drop_first_3_days: { estimate: 0.71, ci_low: 0.22, ci_high: 1.2, p_value: 0.005 },
  first_session_per_user: { estimate: 0.49, ci_low: 0.04, ci_high: 0.94, p_value: 0.033 },
  logit_platform: { estimate: 0.6, ci_low: 0.17, ci_high: 1.03, p_value: 0.007 },
};

export function resultFor(changedOption: string | null, n: number, rule: DecisionRule): AnalysisResult {
  const row = OVERRIDES[changedOption ?? "baseline"] ?? OVERRIDES["baseline"]!;
  return {
    ...row,
    n,
    metric: rule.metric,
    extra: { control_rate: 0.0842, treatment_rate: Number((0.0842 + row.estimate / 100).toFixed(4)) },
  };
}

export function verdictOf(result: AnalysisResult, rule: DecisionRule): string {
  const beats = rule.comparator === "gt" ? result.estimate > rule.threshold : result.estimate < rule.threshold;
  return beats && result.p_value < rule.alpha ? rule.positive_label : rule.negative_label;
}
