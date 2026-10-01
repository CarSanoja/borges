import { useEffect, useReducer } from "react";
import { buildSampleRun, SAMPLE_RUN_ID } from "../../fixtures/sampleRun";
import { eventsUrl, recordingUrl } from "../../shared/api/client";
import { subscribeEvents } from "../../shared/api/sse";
import type { RunEvent, RunSnapshot } from "../../shared/types/contracts";
import { applyEvent, initialSnapshot } from "./reducer";

export type RunSource =
  | { kind: "live"; runId: string }
  | { kind: "replay"; caseId: string; speed: number }
  | { kind: "mock" };

type Action =
  | { type: "event"; event: RunEvent }
  | { type: "reset"; runId: string }
  | { type: "connection_lost" };

const MAX_MOCK_DELAY_MS = 650;

export function sourceKey(source: RunSource): string {
  if (source.kind === "live") return `live:${source.runId}`;
  if (source.kind === "replay") return `replay:${source.caseId}:${source.speed}`;
  return "mock";
}

export function sourceRunId(source: RunSource): string {
  if (source.kind === "live") return source.runId;
  if (source.kind === "replay") return `replay-${source.caseId}`;
  return SAMPLE_RUN_ID;
}

function reduce(snapshot: RunSnapshot, action: Action): RunSnapshot {
  switch (action.type) {
    case "reset":
      return initialSnapshot(action.runId);
    case "connection_lost":
      if (snapshot.status !== "running") return snapshot;
      return { ...snapshot, status: "failed", error: "Connection to the run was lost." };
    case "event": {
      const next = applyEvent(snapshot, action.event);
      return next.run_id === action.event.run_id ? next : { ...next, run_id: action.event.run_id };
    }
  }
}

export function scheduleMock(events: readonly RunEvent[], emit: (event: RunEvent) => void): () => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let index = 0;
  const step = () => {
    const event = events[index];
    if (!event) return;
    emit(event);
    index += 1;
    const next = events[index];
    if (!next) return;
    const delay = Math.min(Math.max((next.ts - event.ts) * 1000, 0), MAX_MOCK_DELAY_MS);
    timer = setTimeout(step, delay);
  };
  timer = setTimeout(step, 250);
  return () => clearTimeout(timer);
}

export function useRun(source: RunSource): RunSnapshot {
  const key = sourceKey(source);
  const [snapshot, dispatch] = useReducer(reduce, source, (s) => initialSnapshot(sourceRunId(s)));

  useEffect(() => {
    dispatch({ type: "reset", runId: sourceRunId(source) });
    const emit = (event: RunEvent) => dispatch({ type: "event", event });
    if (source.kind === "mock") return scheduleMock(buildSampleRun(), emit);
    const url =
      source.kind === "live" ? eventsUrl(source.runId, 0) : recordingUrl(source.caseId, source.speed);
    return subscribeEvents(url, emit, () => dispatch({ type: "connection_lost" }));
  }, [key]);

  return snapshot;
}
