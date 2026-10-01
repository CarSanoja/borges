import type { RunEvent } from "../shared/types/contracts";
import recorded from "./recordedCheckout.json";

export const RECORDED_RUN_ID = "recorded-checkout";

export function recordedRun(): RunEvent[] {
  return recorded as unknown as RunEvent[];
}
