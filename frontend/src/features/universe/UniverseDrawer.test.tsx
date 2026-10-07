import { fireEvent, render, screen } from "@testing-library/react";
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
    expect(screen.getAllByRole("button", { name: "Show code" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Reproduced from scratch")).toBeInTheDocument();
  });

  it("puts the result and the Reproduce block before the per-step choices", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    const result = document.querySelector(".u-result")!;
    const reproduce = screen.getByRole("region", { name: "Reproduce" });
    const steps = document.querySelector(".u-steps")!;
    expect(result.compareDocumentPosition(reproduce) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(reproduce.compareDocumentPosition(steps) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("keeps each step's code closed until its toggle is used from the keyboard", async () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    expect(screen.queryByLabelText(/^Code for/)).toBeNull();
    const toggle = screen.getAllByRole("button", { name: "Show code" })[0]!;
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    toggle.focus();
    await userEvent.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(toggle).toHaveTextContent("Hide code");
    expect(screen.getAllByLabelText(/^Code for/)).toHaveLength(1);
    await userEvent.keyboard(" ");
    expect(screen.queryByLabelText(/^Code for/)).toBeNull();
  });

  it("states that errors are clustered when the chosen option sets cluster_by", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    const detail = deriveDetail(snapshot, flipId) as UniverseDetail;
    const chosen = detail.steps[0]!.option.id;
    const plan = snapshot.plan!;
    const clustered = {
      ...snapshot,
      plan: {
        ...plan,
        steps: plan.steps.map((step, index) =>
          index === 0 ? { ...step, options: step.options.map((o) => (o.id === chosen ? { ...o, cluster_by: "prof" } : o)) } : step,
        ),
      },
    };
    render(<UniverseDrawer runId={null} snapshot={clustered} universeId={flipId} onClose={() => undefined} />);
    const lines = screen.getAllByText(
      "Errors clustered by prof: the harness fits the model with cluster-robust errors on that column, overriding the covariance the code asks for.",
    );
    expect(lines).toHaveLength(1);
  });

  it("shows no clustering line when no chosen option sets cluster_by", () => {
    const flipId = snapshot.flip?.universe_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={flipId} onClose={() => undefined} />);
    expect(screen.queryByText(/Errors clustered by/)).toBeNull();
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
    expect(await screen.findByText(`uv run borges reproduce --case checkout_ab --universe ${flipId}`)).toBeInTheDocument();
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

  it("closes on Escape straight after opening, before any focus moves inside", () => {
    const onClose = vi.fn();
    const baselineId = snapshot.garden.baseline_id ?? "";
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={baselineId} onClose={onClose} />);
    expect(screen.getByRole("dialog")).toHaveFocus();
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("is a labelled modal dialog that takes focus, traps Tab and gives focus back", async () => {
    const baselineId = snapshot.garden.baseline_id ?? "";
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const { rerender } = render(
      <UniverseDrawer runId={null} snapshot={snapshot} universeId={baselineId} onClose={() => undefined} />,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName(baselineId);
    expect(dialog.contains(document.activeElement)).toBe(true);
    for (let i = 0; i < 12; i += 1) {
      await userEvent.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
    await userEvent.tab({ shift: true });
    expect(dialog.contains(document.activeElement)).toBe(true);
    rerender(<UniverseDrawer runId={null} snapshot={snapshot} universeId={null} onClose={() => undefined} />);
    expect(opener).toHaveFocus();
    opener.remove();
  });

  it("renders nothing without a selection", () => {
    render(<UniverseDrawer runId={null} snapshot={snapshot} universeId={null} onClose={() => undefined} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
