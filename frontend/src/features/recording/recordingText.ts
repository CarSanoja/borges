import type { LiveRecordingSummary, RecordingSource, RecordingStamp } from "../../shared/types/contracts";

export const SCRIPTED_STATEMENT = "Scripted replay of hand-built fixtures: no model was called";

export function recordedDate(recordedAt: string): string {
  return recordedAt.slice(0, 10);
}

export function formatCost(costUsd: number): string {
  return costUsd.toFixed(4);
}

export function liveStatement(live: LiveRecordingSummary): string {
  const tokens = (live.tokens_in + live.tokens_out).toLocaleString("en-US");
  return `Recorded live on Nemotron via Nebius Token Factory, ${recordedDate(live.recorded_at)}: ${live.llm_calls} calls, ${tokens} tokens, $${formatCost(live.cost_usd)}`;
}

export function statementFor(source: RecordingSource, live: LiveRecordingSummary | null | undefined): string | null {
  if (source === "scripted") return SCRIPTED_STATEMENT;
  return live ? liveStatement(live) : null;
}

export function pickSource(requested: RecordingSource | null, live: LiveRecordingSummary | null | undefined, scripted: boolean): RecordingSource {
  if (requested === "scripted" && scripted) return "scripted";
  if (live) return "live";
  return "scripted";
}

export function stampStatement(stamp: RecordingStamp | null | undefined): string | null {
  if (!stamp) return null;
  const commit = stamp.commit ? `${stamp.commit}${stamp.dirty ? "+dirty" : ""}` : "an unrecorded commit";
  const when = stamp.recorded_at ? ` on ${recordedDate(stamp.recorded_at)}` : "";
  const backend = stamp.backend ? `, ${stamp.backend}` : "";
  return `recorded live at ${commit}${when}${backend}`;
}
