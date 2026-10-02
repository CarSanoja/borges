import type { LiveRecordingSummary } from "../shared/types/contracts";

export const LIVE_CHECKOUT: LiveRecordingSummary = {
  recorded_at: "2026-10-02T11:11:56Z",
  models: {
    planner: "nvidia/nemotron-3-super-120b-a12b",
    coder: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    narrator: "nvidia/Nemotron-3-Ultra-550b-a55b",
  },
  llm_calls: 22,
  tokens_in: 33499,
  tokens_out: 9371,
  cost_usd: 0.0069732,
  verdict: "DON'T SHIP",
  flipped_verdict: "SHIP",
  flip_kind: "direction",
  universes: 8,
};
