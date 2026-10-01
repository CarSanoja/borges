import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { RunSnapshot } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { UniverseDrawer } from "./UniverseDrawer";

function withCode(base: RunSnapshot): RunSnapshot {
  if (!base.plan) return base;
  const steps = base.plan.steps.map((step) => ({
    ...step,
    options: step.options.map((option) => ({ ...option, code: `df = df[df.x > 2]  # keep\nreturn "a"` })),
  }));
  return { ...base, plan: { ...base.plan, steps } };
}

const snapshot = withCode(foldEvents("r1", buildSampleRun("r1")));

describe("UniverseDrawer", () => {
  it("shows changed steps, code and the reproduced badge", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    const changed = (snapshot.garden.universes[flipId]?.changed.length ?? -1);
    expect(document.querySelectorAll('[data-changed="true"]')).toHaveLength(changed);
    expect(screen.getAllByLabelText(/^Code for/).length).toBeGreaterThan(0);
    expect(screen.getByText("Reproduced from scratch")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  it("falls back to the decision rule metric when the result has none", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    const universe = snapshot.garden.universes[flipId]!;
    const blank = {
      ...snapshot,
      garden: {
        ...snapshot.garden,
        universes: { ...snapshot.garden.universes, [flipId]: { ...universe, result: { ...universe.result!, metric: "" } } },
      },
    };
    render(<UniverseDrawer runId={null} snapshot={blank} universeId={flipId} onClose={() => undefined} />);
    expect(document.querySelector(".u-result")?.textContent?.trim().startsWith(blank.decision_rule!.metric)).toBe(true);
  });

  it("closes on Escape and on the close button", async () => {
    const onClose = vi.fn();
    const baselineId = snapshot.garden.baseline_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={baselineId} onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("renders nothing without a selection", () => {
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={null} onClose={() => undefined} />);
    expect(screen.queryByLabelText("Universe")).toBeNull();
  });
});
