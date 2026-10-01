import type { DecisionInfluence, RunSnapshot } from "../../shared/types/contracts";

export function computeInfluences(snapshot: RunSnapshot): DecisionInfluence[] {
  const universes = Object.values(snapshot.garden.universes);
  const baselineId = snapshot.garden.baseline_id;
  const baseline = universes.find((u) => u.id === baselineId || u.kind === "baseline");
  if (!baseline || baseline.status !== "done" || !baseline.result) return [];
  const origin = baseline.result.estimate;
  const finished = universes.filter(
    (u) => u.status === "done" && u.result !== null && u.kind !== "baseline" && u.kind !== "verification",
  );
  const stepIds = new Set(finished.flatMap((u) => u.changed));
  const titles = new Map((snapshot.plan?.steps ?? []).map((s) => [s.id, s.title]));

  return [...stepIds].map((stepId) => {
    const group = finished.filter((u) => u.changed.includes(stepId));
    const deltas = group.map((u) => Math.abs((u.result?.estimate ?? origin) - origin));
    return {
      step_id: stepId,
      title: titles.get(stepId) ?? stepId,
      mean_abs_delta: deltas.reduce((a, b) => a + b, 0) / deltas.length,
      max_abs_delta: Math.max(...deltas),
      flips: group.filter((u) => u.flipped === true).length,
      n_alternatives: group.length,
    };
  });
}

export function rankInfluences(items: readonly DecisionInfluence[]): DecisionInfluence[] {
  return [...items].sort((a, b) => b.max_abs_delta - a.max_abs_delta || b.flips - a.flips);
}
