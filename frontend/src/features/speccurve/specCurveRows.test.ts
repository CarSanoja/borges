import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { buildPoints, buildRows } from "./specCurveData";

describe("buildRows", () => {
  it("keeps every plan step while the run is still going", () => {
    const snapshot = foldEvents("t", buildSampleRun("t"));
    const running = { ...snapshot, status: "running" as const };
    const steps = snapshot.plan?.steps.length ?? 0;
    expect(buildRows(running, buildPoints(running))).toHaveLength(steps);
  });

  it("drops lanes no finished universe ever changes once the run is complete", () => {
    const snapshot = foldEvents("t", buildSampleRun("t"));
    const done = { ...snapshot, status: "completed" as const };
    const points = buildPoints(done);
    const rows = buildRows(done, points);
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(points.some((p) => p.alternatives.has(row.stepId))).toBe(true);
    }
  });
});
