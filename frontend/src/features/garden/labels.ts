import type { AnalysisPlan, CheckpointNode } from "../../shared/types/contracts";

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
