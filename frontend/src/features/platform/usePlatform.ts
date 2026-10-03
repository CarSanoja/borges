import { useEffect, useState } from "react";
import { getPlatform } from "../../shared/api/client";
import type { PlatformStatus } from "./platformTypes";

export type PlatformState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; platform: PlatformStatus };

export function usePlatform(): PlatformState {
  const [state, setState] = useState<PlatformState>({ status: "loading" });
  useEffect(() => {
    let active = true;
    getPlatform()
      .then((platform) => active && setState({ status: "ready", platform }))
      .catch((error: unknown) => {
        if (active) setState({ status: "error", message: error instanceof Error ? error.message : "Platform status unavailable" });
      });
    return () => {
      active = false;
    };
  }, []);
  return state;
}
