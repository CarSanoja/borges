import type { AnalysisPlan, CheckpointNode, Universe } from "../../shared/types/contracts";

export interface NodeLabel {
  stepTitle: string;
  optionLabel: string;
}

export function resolveLabel(
  plan: AnalysisPlan | null,
  node: Pick<CheckpointNode, "step_id" | "option_id">,
): NodeLabel {
  if (!node.step_id) {
    return { stepTitle: "Dataset", optionLabel: plan?.dataset.name ?? "Dataset" };
  }
  const step = plan?.steps.find((s) => s.id === node.step_id);
  const option = step?.options.find((o) => o.id === node.option_id);
  return {
    stepTitle: step?.title ?? node.step_id,
    optionLabel: option?.label ?? node.option_id ?? "",
  };
}

export function formatNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs !== 0 && abs < 0.001) return value.toExponential(1);
  if (abs >= 1000) return value.toFixed(0);
  return value.toFixed(abs >= 10 ? 2 : 3);
}

export function formatP(p: number): string {
  return p < 0.001 ? "< 0.001" : p.toFixed(3);
}

function changedChoices(plan: AnalysisPlan | null, universe: Universe): string {
  const parts = universe.changed.map((stepId) => {
    const step = plan?.steps.find((s) => s.id === stepId);
    const option = step?.options.find((o) => o.id === universe.choices[stepId]);
    return `${step?.title ?? stepId}: ${option?.label ?? universe.choices[stepId] ?? ""}`;
  });
  return parts.length > 0 ? `changes ${parts.join("; ")}` : "default choices";
}

export function universeAriaLabel(plan: AnalysisPlan | null, universe: Universe): string {
  const kind = universe.kind === "baseline" ? "Baseline universe" : `Universe ${universe.id}`;
  const verdict = universe.verdict ?? universe.status;
  const result = universe.result ? `, estimate ${formatNumber(universe.result.estimate)}` : "";
  const flip = universe.flipped ? ", flips the verdict" : "";
  return `${kind}, ${changedChoices(plan, universe)}, verdict ${verdict}${result}${flip}`;
}
