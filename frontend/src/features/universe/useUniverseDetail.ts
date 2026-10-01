import { useEffect, useMemo, useState } from "react";
import { getUniverse } from "../../shared/api/client";
import type { RunSnapshot, UniverseDetail } from "../../shared/types/contracts";
import { deriveDetail } from "./derive";

export function useUniverseDetail(
  runId: string | null,
  snapshot: RunSnapshot,
  universeId: string | null,
): UniverseDetail | null {
  const derived = useMemo(
    () => (universeId ? deriveDetail(snapshot, universeId, runId) : null),
    [snapshot, universeId, runId],
  );
  const [loaded, setLoaded] = useState<{ key: string; detail: UniverseDetail } | null>(null);
  const finished = universeId ? snapshot.garden.universes[universeId]?.status : undefined;

  useEffect(() => {
    if (!runId || !universeId || finished !== "done") return;
    let active = true;
    getUniverse(runId, universeId).then(
      (detail) => {
        if (active) setLoaded({ key: `${runId}:${universeId}`, detail });
      },
      () => undefined,
    );
    return () => {
      active = false;
    };
  }, [runId, universeId, finished]);

  if (runId && universeId && loaded?.key === `${runId}:${universeId}`) return loaded.detail;
  return derived;
}
