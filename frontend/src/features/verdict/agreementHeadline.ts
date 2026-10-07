import type { AnalysisResult, DecisionRule, RunSnapshot, Universe } from "../../shared/types/contracts";
import { formatP } from "./verdictFormat";
import { activeRule, agreementShare, originalResult, originalVerdict } from "./verdictModel";

export interface AgreementHeadline {
  agree: number;
  total: number;
  inconclusive: boolean;
  suffix: string;
  verb: string;
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

export function agreementHeadline(snapshot: RunSnapshot): AgreementHeadline | null {
  const share = agreementShare(snapshot);
  const report = snapshot.report;
  if (!share || !report) return null;
  const rule = activeRule(snapshot);
  const distinct = report.n_distinct_results ?? 0;
  const suffix = distinct > 0 && distinct < share.total ? ` (${distinct} distinct results)` : "";
  const inconclusive = isInconclusive(originalVerdict(snapshot), originalResult(snapshot), rule);
  return {
    ...share,
    inconclusive,
    suffix,
    verb: inconclusive ? "paths are also inconclusive" : "paths agree",
    pLine: inconclusive && rule ? pLineFor(smallestP(snapshot.garden.universes), rule.alpha) : null,
  };
}
