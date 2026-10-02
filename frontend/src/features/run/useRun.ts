import { useEffect, useReducer } from "react";
import { RECORDED_RUN_ID, recordedRun } from "../../fixtures/recordedRun";
import { ApiError, eventsUrl, getCase, getRun, recordingUrl } from "../../shared/api/client";
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
  | { type: "connection_lost" }
  | { type: "run_gone" }
  | { type: "case_gone" };

const MAX_MOCK_DELAY_MS = 650;

export const RUN_GONE_MESSAGE =
  "This run no longer exists on this server (runs are cleared on redeploy). Watch the recorded run instead.";

export const CASE_GONE_MESSAGE = "This case does not exist on this server.";

export function isNotFound(snapshot: RunSnapshot): boolean {
  return snapshot.error === RUN_GONE_MESSAGE || snapshot.error === CASE_GONE_MESSAGE;
}

export function sourceKey(source: RunSource): string {
  if (source.kind === "live") return `live:${source.runId}`;
  if (source.kind === "replay") return `replay:${source.caseId}:${source.speed}`;
  return "mock";
}

export function sourceRunId(source: RunSource): string {
  if (source.kind === "live") return source.runId;
  if (source.kind === "replay") return `replay-${source.caseId}`;
  return RECORDED_RUN_ID;
}

function reduce(snapshot: RunSnapshot, action: Action): RunSnapshot {
  switch (action.type) {
    case "reset":
      return initialSnapshot(action.runId);
    case "connection_lost":
      if (snapshot.status !== "running") return snapshot;
      return { ...snapshot, status: "failed", error: "Connection to the run was lost." };
    case "run_gone":
      if (snapshot.status !== "running") return snapshot;
      return { ...snapshot, status: "failed", error: RUN_GONE_MESSAGE };
    case "case_gone":
      if (snapshot.status !== "running") return snapshot;
      return { ...snapshot, status: "failed", error: CASE_GONE_MESSAGE };
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
    if (source.kind === "mock") return scheduleMock(recordedRun(), emit);
    const url =
      source.kind === "live" ? eventsUrl(source.runId, 0) : recordingUrl(source.caseId, source.speed);
    let active = true;
    const onLost = () => {
      if (source.kind === "replay") {
        getCase(source.caseId).then(
          () => active && dispatch({ type: "connection_lost" }),
          (cause) =>
            active &&
            dispatch({ type: cause instanceof ApiError && cause.status === 404 ? "case_gone" : "connection_lost" }),
        );
        return;
      }
      if (source.kind !== "live") return dispatch({ type: "connection_lost" });
      getRun(source.runId).then(
        () => active && dispatch({ type: "connection_lost" }),
        (cause) =>
          active &&
          dispatch({ type: cause instanceof ApiError && cause.status === 404 ? "run_gone" : "connection_lost" }),
      );
    };
    const unsubscribe = subscribeEvents(url, emit, onLost);
    return () => {
      active = false;
      unsubscribe();
    };
  }, [key]);

  return snapshot;
}
