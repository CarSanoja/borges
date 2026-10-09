import type { RunSnapshot } from "../../shared/types/contracts";
import { formatNumber } from "./verdictFormat";
import { activeFlip, activeRule, originalResult, originalVerdict } from "./verdictModel";

export function nullResultSentence(snapshot: RunSnapshot): string | null {
  const report = snapshot.report;
  const result = originalResult(snapshot);
  const rule = activeRule(snapshot);
  if (!report || !result || !rule || activeFlip(snapshot)) return null;
  if (originalVerdict(snapshot) !== rule.negative_label) return null;
  const upper = rule.comparator === "gt";
  const bound = upper ? result.ci_high : result.ci_low;
  if (!Number.isFinite(bound)) return null;
  const ruled = `The data rule out an effect ${upper ? "above" : "below"} ${formatNumber(bound)} (${upper ? "upper" : "lower"} end of the 95% interval)`;
  const agreed =
    report.n_universes > 1
      ? "every analysis path agreed there is no clear evidence"
      : "only the default analysis ran, and it found no clear evidence";
  return `${ruled}; ${agreed}, which is not proof of no effect.`;
}
