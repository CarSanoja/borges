import type { RunEvent, RunEventType } from "../types/contracts";

export const EVENT_TYPES: readonly RunEventType[] = [
  "run.started",
  "stage",
  "plan.ready",
  "option.coded",
  "option.proposed",
  "option.judged",
  "checkpoint.created",
  "universe.started",
  "universe.finished",
  "flip.found",
  "flip.verified",
  "usage",
  "report.ready",
  "run.finished",
  "run.failed",
];

const TERMINAL: ReadonlySet<RunEventType> = new Set(["run.finished", "run.failed"]);

export function subscribeEvents(
  url: string,
  onEvent: (event: RunEvent) => void,
  onError?: (error: Event) => void,
): () => void {
  const source = new EventSource(url);
  const listeners = EVENT_TYPES.map((type) => {
    const listener = (message: MessageEvent<string>) => {
      let event: RunEvent;
      try {
        event = JSON.parse(message.data) as RunEvent;
      } catch {
        return;
      }
      onEvent(event);
      if (TERMINAL.has(type)) source.close();
    };
    source.addEventListener(type, listener as EventListener);
    return { type, listener };
  });
  source.onerror = (error) => {
    if (source.readyState === EventSource.CLOSED) onError?.(error);
  };
  return () => {
    for (const { type, listener } of listeners) {
      source.removeEventListener(type, listener as EventListener);
    }
    source.close();
  };
}
