import type { RunSnapshot, StageName } from "../../shared/types/contracts";

export type StageState = "done" | "active" | "pending";

export const STAGES: ReadonlyArray<{ name: StageName; label: string }> = [
  { name: "profiling", label: "Profiling" },
  { name: "planning", label: "Planning" },
  { name: "coding", label: "Coding" },
  { name: "baseline", label: "Baseline" },
  { name: "single_flips", label: "Single flips" },
  { name: "adversary", label: "Adversary" },
  { name: "pair_flips", label: "Pair flips" },
  { name: "verifying", label: "Verifying" },
  { name: "narrating", label: "Narrating" },
];

export function stageState(snapshot: RunSnapshot, name: StageName): StageState {
  const status = snapshot.stages[name];
  if (status === "done") return "done";
  if (status === "started") return snapshot.status === "running" ? "active" : "pending";
  return "pending";
}
