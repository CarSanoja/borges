import type { Universe } from "../../shared/types/contracts";

export type Tone = "baseline" | "agree" | "flipped" | "pending";

export const TONE_VAR: Record<Tone, string> = {
  baseline: "var(--gold)",
  agree: "var(--verdigris)",
  flipped: "var(--vermilion)",
  pending: "var(--paper-700)",
};

export const TONE_LABEL: Record<Tone, string> = {
  baseline: "Original path",
  agree: "Agrees with the original",
  flipped: "Changes the verdict",
  pending: "Pending or failed",
};

export function universeTone(universe: Universe | undefined, baselineId: string | null): Tone {
  if (!universe || universe.status !== "done" || !universe.result) return "pending";
  if (universe.id === baselineId || universe.kind === "baseline") return "baseline";
  return universe.flipped ? "flipped" : "agree";
}
