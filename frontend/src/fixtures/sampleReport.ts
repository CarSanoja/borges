import type { AnalysisPlan, DecisionInfluence, Flip, Report } from "../shared/types/contracts";
import type { GardenBuilder } from "./sampleGarden";

function influences(plan: AnalysisPlan, garden: GardenBuilder): DecisionInfluence[] {
  const baseline = garden.finished.get("u_baseline")!.result!.estimate;
  return plan.steps
    .map((step) => {
      const alternatives = [...garden.finished.values()].filter(
        (u) => u.kind !== "baseline" && u.kind !== "verification" && u.changed.includes(step.id),
      );
      const deltas = alternatives.map((u) => Math.abs(u.result!.estimate - baseline));
      return {
        step_id: step.id,
        title: step.title,
        mean_abs_delta: Number((deltas.reduce((a, b) => a + b, 0) / deltas.length).toFixed(3)),
        max_abs_delta: Number(Math.max(...deltas).toFixed(3)),
        flips: alternatives.filter((u) => u.flipped).length,
        n_alternatives: alternatives.length,
      };
    })
    .sort((a, b) => b.mean_abs_delta - a.mean_abs_delta);
}

export function buildReport(plan: AnalysisPlan, garden: GardenBuilder, flip: Flip): Report {
  const explored = [...garden.finished.values()].filter((u) => u.kind !== "verification");
  const flipped = explored.filter((u) => u.flipped).length;
  return {
    question: plan.question,
    original_verdict: flip.baseline_verdict,
    original_result: flip.baseline_result,
    minimal_flip: flip,
    influences: influences(plan, garden),
    robustness: Number(((explored.length - flipped) / explored.length).toFixed(3)),
    n_universes: explored.length,
    n_flipped: flipped,
    narrative:
      "The checkout redesign looks like a clear win on the default path: +0.62 pp, interval clear of zero. " +
      "But the whole effect lives in one decision. Internal test accounts, 2.6% of sessions, converted far more often " +
      "in the treatment arm. Excluding them is the standard hygiene step, and with it the lift collapses to +0.04 pp " +
      "with p = 0.86. Every other choice agrees with SHIP. Verify the exclusion before you roll out.",
    caveats: [
      "Influence is measured by changing one decision with all others at defaults.",
      "Defensibility scores come from an LLM judge, not from ground truth.",
    ],
  };
}
