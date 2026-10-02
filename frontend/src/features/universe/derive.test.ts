import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { deriveDetail } from "./derive";

const snapshot = foldEvents("r1", buildSampleRun("r1"));

describe("deriveDetail", () => {
  it("returns null for unknown universes", () => {
    expect(deriveDetail(snapshot, "nope")).toBeNull();
  });

  it("builds ordered steps with traces and changed flags", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    const detail = deriveDetail(snapshot, flipId);
    expect(detail).not.toBeNull();
    expect(detail?.steps.map((s) => s.step.id)).toEqual(snapshot.plan?.steps.map((s) => s.id));
    const changedIds = detail?.steps.filter((s) => s.changed).map((s) => s.step.id);
    expect(changedIds).toEqual(snapshot.garden.universes[flipId]?.changed);
    expect(detail?.steps.every((s) => s.trace !== null)).toBe(true);
  });

  it("leaves the reproduce command to the server instead of inventing one", () => {
    const universeId = Object.keys(snapshot.garden.universes).find((id) => id !== snapshot.flip?.universe_id) ?? "";
    const detail = deriveDetail(snapshot, universeId);
    expect(detail?.reproduce_command).toBe("");
    expect(detail?.script_url ?? null).toBeNull();
  });

  it("marks nothing changed for the baseline", () => {
    const baselineId = snapshot.garden.baseline_id ?? "";
    const detail = deriveDetail(snapshot, baselineId);
    expect(detail?.steps.some((s) => s.changed)).toBe(false);
  });
});
