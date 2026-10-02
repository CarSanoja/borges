import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { RunSnapshot } from "../../shared/types/contracts";
import * as client from "../../shared/api/client";
import type { UniverseDetail } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { deriveDetail } from "./derive";
import { UniverseDrawer } from "./UniverseDrawer";

function withCode(base: RunSnapshot): RunSnapshot {
  if (!base.plan) return base;
  const steps = base.plan.steps.map((step) => ({
    ...step,
    options: step.options.map((option) => ({ ...option, code: `df = df[df.x > 2]  # keep\nreturn "a"` })),
  }));
  return { ...base, plan: { ...base.plan, steps } };
}

vi.mock("../../shared/api/client");

const snapshot = withCode(foldEvents("r1", buildSampleRun("r1")));

describe("UniverseDrawer", () => {
  it("shows changed steps, code and the reproduced badge", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    const changed = (snapshot.garden.universes[flipId]?.changed.length ?? -1);
    expect(document.querySelectorAll('[data-changed="true"]')).toHaveLength(changed);
    expect(screen.getAllByLabelText(/^Code for/).length).toBeGreaterThan(0);
    expect(screen.getByText("Reproduced from scratch")).toBeInTheDocument();
  });

  it("shows the command computed by the server for the run, never the stored steps chain", async () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    const derived = deriveDetail(snapshot, flipId) as UniverseDetail;
    vi.mocked(client.getUniverse).mockResolvedValue({
      ...derived,
      reproduce_command: `borges reproduce --case checkout_ab --universe ${flipId}`,
      reproduce_kind: "case",
      script_url: `/api/runs/r1/universes/${flipId}/script`,
      script_filename: `borges_r1_${flipId}.py`,
    });
    render(<UniverseDrawer runId="r1" snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    expect(await screen.findByText(`borges reproduce --case checkout_ab --universe ${flipId}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(screen.queryByText(/python steps\//)).toBeNull();
  });

  it("labels defensibility with the judge score or as an unjudged planner option", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    expect(screen.queryByText("n/a")).toBeNull();
    const facts = Array.from(document.querySelectorAll(".u-facts dd")).map((el) => el.textContent ?? "");
    expect(facts.some((text) => /judged\)|not judged/.test(text))).toBe(true);
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
