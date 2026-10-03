import type { CaseCard } from "../../shared/types/contracts";
import type { RunSource } from "./useRun";

export function hasTrace(source: RunSource, card: CaseCard | null, runId: string | null): boolean {
  if (!runId || source.kind === "mock") return false;
  if (source.kind !== "replay") return true;
  const recording = source.recording;
  return Boolean(recording && card?.traced_sources?.includes(recording));
}
