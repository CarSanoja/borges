import { useCallback, useEffect, useState } from "react";
import { forgetMemory, getMemory } from "../../shared/api/client";
import type { MemorySummary } from "../../shared/types/contracts";

export type MemoryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; summary: MemorySummary };

export function useMemory(): [MemoryState, (dataset?: string) => Promise<string | null>] {
  const [state, setState] = useState<MemoryState>({ status: "loading" });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    getMemory()
      .then((summary) => active && setState({ status: "ready", summary }))
      .catch((error: unknown) => {
        if (active) setState({ status: "error", message: error instanceof Error ? error.message : "Memory unavailable" });
      });
    return () => {
      active = false;
    };
  }, [version]);
  const forget = useCallback(async (dataset?: string) => {
    try {
      await forgetMemory(dataset);
      setVersion((value) => value + 1);
      return null;
    } catch (error: unknown) {
      return error instanceof Error ? error.message : "Could not forget";
    }
  }, []);
  return [state, forget];
}
