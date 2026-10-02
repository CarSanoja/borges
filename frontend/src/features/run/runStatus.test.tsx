import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { RunEvent } from "../../shared/types/contracts";
import { Telemetry } from "../telemetry/Telemetry";
import { stageState } from "../telemetry/stageStates";
import { foldEvents } from "./reducer";
import { statusLabel } from "./runLabels";

const events = buildSampleRun("t");

function indexOf(type: RunEvent["type"], name?: string, status?: string): number {
  return events.findIndex(
    (e) => e.type === type && (!name || (e.type === "stage" && e.data.name === name && e.data.status === status)),
  );
}

describe("run status chip", () => {
  it("is not Complete while Verifying or Narrating are still running", () => {
    for (const stage of ["verifying", "narrating"]) {
      const cut = indexOf("stage", stage, "started");
      const label = statusLabel(foldEvents("t", events.slice(0, cut + 1)));
      expect(label).not.toBe("Complete");
    }
  });

  it("is not Complete between the last stage and run.finished", () => {
    const cut = indexOf("run.finished");
    const label = statusLabel(foldEvents("t", events.slice(0, cut)));
    expect(label).toBe("Finishing");
  });

  it("is Complete only once run.finished arrives", () => {
    expect(statusLabel(foldEvents("t", events))).toBe("Complete");
  });

  it("tolerates option.smoke events without changing the snapshot", () => {
    const smoke: RunEvent = {
      seq: 999,
      ts: 0,
      run_id: "t",
      type: "option.smoke",
      data: { step_id: "s", option_id: "o", status: "repaired", attempts: 2, error: null },
    };
    const base = foldEvents("t", events);
    const next = foldEvents("t", [...events, smoke]);
    expect(next.garden).toEqual(base.garden);
    expect(next.plan).toEqual(base.plan);
  });
});

describe("skipped stages", () => {
  it("renders a stage that never ran in a completed run as skipped, not pending", () => {
    const withoutAdversary = events.filter((e) => !(e.type === "stage" && e.data.name === "adversary"));
    const snapshot = foldEvents("t", withoutAdversary);
    expect(stageState(snapshot, "adversary")).toBe("skipped");
    render(<Telemetry snapshot={snapshot} />);
    const item = screen.getByText("Adversary").closest("li");
    expect(item).toHaveAttribute("data-state", "skipped");
  });

  it("keeps unreached stages pending while the run is still going", () => {
    const cut = indexOf("stage", "baseline", "started");
    const snapshot = foldEvents("t", events.slice(0, cut + 1));
    expect(stageState(snapshot, "narrating")).toBe("pending");
  });
});
