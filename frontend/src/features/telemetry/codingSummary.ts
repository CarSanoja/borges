import type { CodingSummary } from "../../shared/types/contracts";

export function codingSentence(coding: CodingSummary): string {
  const parts = [
    `${coding.smoke_tested} ${coding.smoke_tested === 1 ? "option" : "options"} tested on a sample`,
    `${coding.repaired_after_smoke} repaired after a failing test`,
  ];
  if (coding.failed > 0) parts.push(`${coding.failed} dropped`);
  return parts.join(", ");
}
