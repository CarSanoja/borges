import { useEffect, useState } from "react";
import { RECORDED_RUN_ID, recordedRun } from "../../fixtures/recordedRun";
import type { RunSnapshot } from "../../shared/types/contracts";
import { applyEvent, foldEvents, initialSnapshot } from "../run/reducer";

const MAX_DELAY_MS = 220;
const HOLD_MS = 6000;
const START_MS = 250;

function seedSnapshot(events: ReturnType<typeof recordedRun>): { snapshot: RunSnapshot; next: number } {
  const root = events.findIndex((e) => e.type === "checkpoint.created");
  const next = root < 0 ? 0 : root + 1;
  return { snapshot: foldEvents(RECORDED_RUN_ID, events.slice(0, next)), next };
}

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
}

export function useSampleLoop(): RunSnapshot {
  const [snapshot, setSnapshot] = useState<RunSnapshot>(() => initialSnapshot(RECORDED_RUN_ID));

  useEffect(() => {
    const events = recordedRun();
    const seed = seedSnapshot(events);
    setSnapshot(seed.snapshot);
    if (prefersReducedMotion()) {
      setSnapshot(foldEvents(RECORDED_RUN_ID, events));
      return undefined;
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    let index = seed.next;
    const step = () => {
      const event = events[index];
      if (!event) {
        timer = setTimeout(() => {
          index = seed.next;
          setSnapshot(seed.snapshot);
          timer = setTimeout(step, START_MS);
        }, HOLD_MS);
        return;
      }
      setSnapshot((prev) => applyEvent(prev, event));
      index += 1;
      const next = events[index];
      const delay = next ? Math.min(Math.max((next.ts - event.ts) * 1000, 30), MAX_DELAY_MS) : 0;
      timer = setTimeout(step, delay);
    };
    timer = setTimeout(step, START_MS);
    return () => clearTimeout(timer);
  }, []);

  return snapshot;
}
