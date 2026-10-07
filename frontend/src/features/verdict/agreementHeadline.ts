import type { RunSnapshot } from "../../shared/types/contracts";
import { formatPercent } from "./verdictFormat";

export interface AgreementHeadline {
  percent: string;
  label: string;
  context: string;
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function agreementHeadline(snapshot: RunSnapshot): AgreementHeadline | null {
  const report = snapshot.report;
  if (!report || report.n_universes <= 0) return null;
  const gridBased = report.robustness_basis === undefined || report.robustness_basis === "design_weighted";
  const distinct = report.n_distinct_results ?? report.n_universes;
  return {
    percent: formatPercent(report.robustness_rating ?? report.robustness),
    label: gridBased ? "of the analysis grid agrees" : "of the distinct explored results agree",
    context: `from ${plural(report.n_universes, "explored path", "explored paths")}, ${plural(distinct, "distinct result", "distinct results")}`,
  };
}
