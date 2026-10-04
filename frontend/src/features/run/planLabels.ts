import type { AnalysisPlan } from "../../shared/types/contracts";

function labelTable(plan: AnalysisPlan): Map<string, string | null> {
  const table = new Map<string, string | null>();
  const add = (id: string, label: string) => {
    if (!id.includes("_") || !label) return;
    const known = table.get(id);
    table.set(id, known === undefined || known === label ? label : null);
  };
  for (const step of plan.steps) {
    add(step.id, step.title);
    for (const option of step.options) add(option.id, option.label);
  }
  return table;
}

export function withPlanLabels(text: string, plan: AnalysisPlan | null | undefined): string {
  if (!plan) return text;
  const table = labelTable(plan);
  return text.replace(/[A-Za-z0-9_]+/g, (word) => table.get(word) ?? word);
}
