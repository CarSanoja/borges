import type { CodingSummary } from "../../shared/types/contracts";

export function codingSentence(coding: CodingSummary): string {
  const parts = [
    `${coding.smoke_tested} ${coding.smoke_tested === 1 ? "option" : "options"} tested on a sample`,
    `${coding.repaired_after_smoke} repaired after a failing test`,
  ];
  if (coding.failed > 0) parts.push(`${coding.failed} dropped`);
  const judged = coding.options_dropped_by_judge ?? 0;
  if (judged > 0) parts.push(`${judged} dropped by the defensibility judge`);
  const replaced = coding.defaults_replaced?.length ?? 0;
  if (replaced > 0) parts.push(`${replaced} conventional ${replaced === 1 ? "option" : "options"} replaced by the judge`);
  const armored = coding.options_dropped_by_armor ?? 0;
  if (armored > 0) parts.push(`${armored} dropped by Armor as tool poisoning`);
  return parts.join(", ");
}
