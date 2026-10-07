import type { AnalysisResult, DecisionRule, RunSnapshot, Universe } from "../../shared/types/contracts";
import { formatP, formatPercent } from "./verdictFormat";
import { activeRule, originalResult, originalVerdict } from "./verdictModel";

export interface AgreementHeadline {
  agree: number;
  total: number;
  inconclusive: boolean;
  percent: string;
  label: string;
  context: string;
  pLine: string | null;
}

export function isInconclusive(verdict: string | null, result: AnalysisResult | null, rule: DecisionRule | null): boolean {
  if (!verdict || !result || !rule) return false;
  return verdict === rule.negative_label && result.p_value >= rule.alpha;
}

export function smallestP(universes: Record<string, Universe>): number | null {
  const values = Object.values(universes)
    .filter((u) => u.status === "done" && u.kind !== "verification" && u.result !== null)
    .map((u) => u.result!.p_value)
    .filter((p) => Number.isFinite(p));
  return values.length > 0 ? Math.min(...values) : null;
}

function pLineFor(minP: number | null, alpha: number): string | null {
  if (minP === null) return null;
  const shown = formatP(minP);
  if (minP < alpha) return `The smallest p-value was ${shown}`;
  return `No path reached p < ${alpha}; the smallest p-value was ${shown}`;
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function agreementHeadline(snapshot: RunSnapshot): AgreementHeadline | null {
  const report = snapshot.report;
  if (!report || report.n_universes <= 0) return null;
  const rule = activeRule(snapshot);
  const inconclusive = isInconclusive(originalVerdict(snapshot), originalResult(snapshot), rule);
  const gridBased = report.robustness_basis === undefined || report.robustness_basis === "design_weighted";
  const distinct = report.n_distinct_results ?? report.n_universes;
  return {
    agree: Math.max(0, report.n_universes - report.n_flipped),
    total: report.n_universes,
    inconclusive,
    percent: formatPercent(report.robustness_rating ?? report.robustness),
    label: gridBased ? "of the analysis grid agrees" : "of the distinct explored results agree",
    context: `from ${plural(report.n_universes, "explored path", "explored paths")}, ${plural(distinct, "distinct result", "distinct results")}`,
    pLine: inconclusive && rule ? pLineFor(smallestP(snapshot.garden.universes), rule.alpha) : null,
  };
}
