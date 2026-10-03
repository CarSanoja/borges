import { describe, expect, it } from "vitest";
import type { CaseCard } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "../cases/fallbackCases";
import { hasTrace } from "./hasTrace";

const base = FALLBACK_CASES[0] as CaseCard;

describe("hasTrace", () => {
  it("always links the trace of a live run", () => {
    expect(hasTrace({ kind: "live", runId: "r_1" }, null, "r_1")).toBe(true);
  });

  it("never links a mock run or a missing id", () => {
    expect(hasTrace({ kind: "mock" }, base, "x")).toBe(false);
    expect(hasTrace({ kind: "live", runId: "r" }, null, null)).toBe(false);
  });

  it("links a replay only when that recording has spans", () => {
    const card = { ...base, traced_sources: ["live" as const] };
    const live = { kind: "replay" as const, caseId: card.id, speed: 1, recording: "live" as const };
    const scripted = { ...live, recording: "scripted" as const };
    expect(hasTrace(live, card, "r_x")).toBe(true);
    expect(hasTrace(scripted, card, "r_x")).toBe(false);
  });

  it("hides the trace of a replay while the card is unknown or lists no traced source", () => {
    const live = { kind: "replay" as const, caseId: base.id, speed: 1, recording: "live" as const };
    expect(hasTrace(live, null, "r_x")).toBe(false);
    expect(hasTrace(live, base, "r_x")).toBe(false);
  });
});
