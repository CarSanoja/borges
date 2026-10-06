import type { AnalysisResult, DecisionRule, Flip, RunSnapshot, Universe } from "../../shared/types/contracts";

export function baselineUniverse(snapshot: RunSnapshot): Universe | null {
  const { baseline_id, universes } = snapshot.garden;
  const byId = baseline_id ? universes[baseline_id] : undefined;
  if (byId) return byId;
  return Object.values(universes).find((u) => u.kind === "baseline") ?? null;
}

export function originalResult(snapshot: RunSnapshot): AnalysisResult | null {
  if (snapshot.report) return snapshot.report.original_result;
  if (snapshot.flip) return snapshot.flip.baseline_result;
  const baseline = baselineUniverse(snapshot);
  return baseline?.status === "done" ? baseline.result : null;
}

export function originalVerdict(snapshot: RunSnapshot): string | null {
  if (snapshot.report) return snapshot.report.original_verdict;
  if (snapshot.flip) return snapshot.flip.baseline_verdict;
  const baseline = baselineUniverse(snapshot);
  return baseline?.status === "done" ? baseline.verdict : null;
}

export function activeFlip(snapshot: RunSnapshot): Flip | null {
  return snapshot.flip ?? snapshot.report?.minimal_flip ?? null;
}

export function activeRule(snapshot: RunSnapshot): DecisionRule | null {
  return snapshot.decision_rule ?? snapshot.plan?.decision_rule ?? null;
}

export function exploredCount(snapshot: RunSnapshot): number {
  if (snapshot.report) return snapshot.report.n_universes;
  return Object.values(snapshot.garden.universes).filter((u) => u.status === "done" && u.kind !== "verification").length;
}

export function agreementShare(snapshot: RunSnapshot): { agree: number; total: number } | null {
  const report = snapshot.report;
  if (!report || report.n_universes <= 0) return null;
  return { agree: Math.max(0, report.n_universes - report.n_flipped), total: report.n_universes };
}
