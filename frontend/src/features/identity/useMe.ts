import { useCallback, useEffect, useState } from "react";
import { ApiError, getMe } from "../../shared/api/client";
import type { Me } from "../../shared/types/contracts";

export type MeState =
  | { status: "loading" }
  | { status: "ready"; me: Me }
  | { status: "rejected"; message: string }
  | { status: "unavailable" };

export function useMe(): [MeState, () => void] {
  const [state, setState] = useState<MeState>({ status: "loading" });
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let active = true;
    getMe()
      .then((me) => active && setState({ status: "ready", me }))
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: "rejected", message: error.message });
        } else {
          setState({ status: "unavailable" });
        }
      });
    return () => {
      active = false;
    };
  }, [version]);
  const refresh = useCallback(() => setVersion((value) => value + 1), []);
  return [state, refresh];
}
