import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { StageTimeline } from "./StageTimeline";

const done = foldEvents("r1", buildSampleRun("r1"));

describe("StageTimeline", () => {
  it("says the flip was not re-executed instead of Verifying (skipped)", () => {
    const snapshot = { ...done, status: "completed" as const, stages: { ...done.stages, verifying: undefined } };
    render(<StageTimeline snapshot={snapshot} />);
    expect(screen.getByText("Flip not re-executed")).toBeInTheDocument();
    expect(screen.queryByText(/Verifying/)).toBeNull();
  });
});
