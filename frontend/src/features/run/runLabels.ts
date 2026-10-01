import type { DecisionRule, RunSnapshot, StageName } from "../../shared/types/contracts";

const STAGE_LABELS: Record<StageName, string> = {
  profiling: "Reading the data",
  planning: "Planning the analysis",
  coding: "Writing branch code",
  baseline: "Walking the original path",
  single_flips: "Forking every decision",
  adversary: "The adversary argues",
  pair_flips: "Combining decisions",
  verifying: "Verifying the flip",
  narrating: "Writing the report",
};

const STAGE_ORDER = Object.keys(STAGE_LABELS) as StageName[];

export function describeRule(rule: DecisionRule): string {
  const sign = rule.comparator === "gt" ? ">" : "<";
  return `${rule.positive_label} if ${rule.metric} ${sign} ${rule.threshold} at p < ${rule.alpha}`;
}

export function currentStage(snapshot: RunSnapshot): StageName | null {
  const active = STAGE_ORDER.filter((name) => snapshot.stages[name] === "started");
  return active.length ? (active[active.length - 1] ?? null) : null;
}

export function statusLabel(snapshot: RunSnapshot): string {
  if (snapshot.status === "failed") return "Failed";
  if (snapshot.status === "completed") return "Complete";
  const stage = currentStage(snapshot);
  return stage ? STAGE_LABELS[stage] : "Starting";
}
