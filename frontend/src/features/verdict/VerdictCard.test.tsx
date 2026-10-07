import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { VerdictCard } from "./VerdictCard";

const events = buildSampleRun("t");

function until(type: string, name?: string) {
  const index = events.findIndex((e) => e.type === type && (!name || (e.type === "stage" && e.data.name === name)));
  return foldEvents("t", events.slice(0, index));
}

describe("VerdictCard", () => {
  it("shows the walking state with the current stage before a baseline", () => {
    render(<VerdictCard snapshot={until("stage", "baseline")} />);
    expect(screen.getByText("Walking the garden...")).toBeInTheDocument();
    expect(document.querySelector(".vc-stage")).not.toBeEmptyDOMElement();
  });

  it("shows the original verdict and robustness after the report", () => {
    const snapshot = foldEvents("t", events);
    render(<VerdictCard snapshot={snapshot} />);
    expect(screen.getByText(snapshot.report!.original_verdict)).toBeInTheDocument();
    const { n_universes, robustness } = snapshot.report!;
    expect(screen.getByTestId("vc-agree")).toHaveTextContent(`${Math.round(robustness * 100)}% of the analysis grid agrees`);
    expect(screen.getByTestId("vc-agree-context")).toHaveTextContent(`from ${n_universes} explored paths`);
  });

  it("reveals the flip with changes and the reproduced badge", () => {
    const snapshot = foldEvents("t", events);
    render(<VerdictCard snapshot={{ ...snapshot, flip: { ...snapshot.flip!, kind: "direction" } }} />);
    expect(screen.getByText("One defensible change reverses it:")).toBeInTheDocument();
    expect(screen.getByText(snapshot.flip!.flipped_verdict)).toBeInTheDocument();
    expect(screen.getByText(snapshot.flip!.changes[0]!.to_label)).toBeInTheDocument();
    expect(screen.getByText("Reproduced from scratch")).toBeInTheDocument();
  });

  it("reports a clean run in verdigris copy when nothing flips", () => {
    const snapshot = foldEvents("t", events);
    const clean = {
      ...snapshot,
      flip: null,
      report: snapshot.report ? { ...snapshot.report, minimal_flip: null, n_universes: 9 } : null,
    };
    render(<VerdictCard snapshot={clean} />);
    expect(screen.getByText("No defensible flip found")).toBeInTheDocument();
    expect(screen.queryByText("One defensible change reverses it:")).not.toBeInTheDocument();
  });

  it("says the decision was not tested when only the default analysis ran", () => {
    const snapshot = foldEvents("t", events);
    const lone = {
      ...snapshot,
      flip: null,
      report: snapshot.report ? { ...snapshot.report, minimal_flip: null, n_universes: 1, n_flipped: 0 } : null,
    };
    render(<VerdictCard snapshot={lone} />);
    expect(screen.getByTestId("untested")).toHaveTextContent("Not tested: only the default analysis ran");
    expect(screen.queryByText("No defensible flip found")).toBeNull();
  });

  it("warns when the flip did not reproduce", () => {
    const snapshot = foldEvents("t", events);
    const flip = { ...snapshot.flip!, reproduced: false };
    render(<VerdictCard snapshot={{ ...snapshot, flip }} />);
    expect(screen.getByText("Not reproduced on a fresh re-execution: treat as unconfirmed")).toBeInTheDocument();
    expect(screen.queryByText("Reproduced from scratch")).toBeNull();
  });

  it("does not warn when the flip reproduced", () => {
    render(<VerdictCard snapshot={foldEvents("t", events)} />);
    expect(screen.queryByText(/treat as unconfirmed/)).toBeNull();
  });

  it("shows how many universes could not run", () => {
    const snapshot = foldEvents("t", events);
    const report = { ...snapshot.report!, n_failed: 2, failed: ["a/b: boom"] };
    render(<VerdictCard snapshot={{ ...snapshot, report }} />);
    expect(screen.getByText(`${report.n_universes + 2} explored, 2 could not run`)).toBeInTheDocument();
  });

  it("shows no failure line when every universe ran", () => {
    render(<VerdictCard snapshot={foldEvents("t", events)} />);
    expect(screen.queryByText(/could not run/)).toBeNull();
  });

  it("says a direction flip changes side of the threshold, with the numbers", () => {
    const snapshot = foldEvents("t", events);
    const flip = {
      ...snapshot.flip!,
      baseline_result: { ...snapshot.flip!.baseline_result, estimate: 0.53, p_value: 0.008 },
      flipped_result: { ...snapshot.flip!.flipped_result, estimate: -0.14, p_value: 0.43 },
    };
    const rule = { ...snapshot.decision_rule!, threshold: 0, comparator: "gt" as const };
    render(<VerdictCard snapshot={{ ...snapshot, flip, decision_rule: rule }} />);
    const kind = document.querySelector(".vc-kind");
    expect(kind?.getAttribute("data-kind")).toBe("direction");
    expect(kind?.textContent).toMatch(/Direction flip/);
    expect(kind?.textContent).toMatch(/changes side of the threshold/);
  });

  it("says a significance flip weakens the evidence without reversing the effect", () => {
    const snapshot = foldEvents("t", events);
    const flip = {
      ...snapshot.flip!,
      baseline_result: { ...snapshot.flip!.baseline_result, estimate: 1.337, p_value: 0.00056 },
      flipped_result: { ...snapshot.flip!.flipped_result, estimate: 1.204, p_value: 0.055 },
    };
    const rule = { ...snapshot.decision_rule!, threshold: 1, comparator: "gt" as const, alpha: 0.05 };
    render(<VerdictCard snapshot={{ ...snapshot, flip, decision_rule: rule }} />);
    const kind = document.querySelector(".vc-kind");
    expect(kind?.getAttribute("data-kind")).toBe("significance");
    expect(kind?.textContent).toMatch(/1\.34 to 1\.20/);
    expect(kind?.textContent).toMatch(/0\.00056 to 0\.055/);
    expect(kind?.textContent).toMatch(/only p crosses 0.05/);
  });

  it("shows the effect range across explored universes next to robustness", () => {
    const snapshot = foldEvents("t", events);
    const estimates = Object.values(snapshot.garden.universes)
      .filter((u) => u.status === "done" && u.kind !== "verification")
      .map((u) => u.result!.estimate);
    render(<VerdictCard snapshot={snapshot} />);
    const range = document.querySelector(".vc-range");
    expect(range?.textContent).toContain(`Effect range across ${estimates.length} universes`);
    expect(range?.textContent).toMatch(/to/);
    expect(screen.getByText(/nearest crossing it found/)).toBeInTheDocument();
  });

  it("does not clamp the rationale of a change", () => {
    const snapshot = foldEvents("t", events);
    render(<VerdictCard snapshot={snapshot} />);
    const why = document.querySelector(".vc-change__why");
    expect(why?.textContent).toBe(snapshot.flip!.changes[0]!.rationale);
    expect(document.querySelector(".vc-command")).toBeNull();
  });
});

describe("VerdictCard search summary", () => {
  const search = { levels_explored: 2, max_combinations_per_level: 10, universe_budget: 24, universes_used: 24, budget_exhausted: true };

  it("states the bounded search on the flipped face and says when the budget ran out", () => {
    const snapshot = foldEvents("t", events);
    render(<VerdictCard snapshot={{ ...snapshot, report: { ...snapshot.report!, search } }} />);
    expect(screen.getByText(/Smallest flip found: \d+ explored of a 24-universe budget, 2 levels\./)).toBeInTheDocument();
    expect(screen.getByText(/24-universe budget ran out/)).toBeInTheDocument();
  });

  it("states executed and budgeted universes once, never two conflicting counts", () => {
    const snapshot = foldEvents("t", events);
    const clean = {
      ...snapshot,
      flip: null,
      report: { ...snapshot.report!, minimal_flip: null, n_universes: 7, n_flipped: 0, search: { ...search, universe_budget: 40, budget_exhausted: false } },
    };
    render(<VerdictCard snapshot={clean} />);
    expect(screen.getByText(/No flip found: 7 explored of a 40-universe budget/)).toBeInTheDocument();
    expect(screen.getByTestId("vc-agree")).toHaveTextContent("of the analysis grid agrees");
    expect(screen.queryByText(/within 40/)).toBeNull();
    expect(screen.queryByText(/found in 7 universes/)).toBeNull();
  });

  it("omits the budget warning when the search finished within budget", () => {
    const snapshot = foldEvents("t", events);
    const done = { ...search, levels_explored: 1, budget_exhausted: false };
    render(<VerdictCard snapshot={{ ...snapshot, report: { ...snapshot.report!, search: done } }} />);
    expect(screen.getByText(/explored of a 24-universe budget, 1 level\./)).toBeInTheDocument();
    expect(screen.queryByText(/search budget ran out/)).toBeNull();
  });

  it("renders without a summary for old recordings", () => {
    const snapshot = foldEvents("t", events);
    render(<VerdictCard snapshot={{ ...snapshot, report: { ...snapshot.report!, search: undefined } }} />);
    expect(screen.queryByText(/Smallest flip found:/)).toBeNull();
  });

  it("uses the recorded kind when present and computes it when missing", () => {
    const snapshot = foldEvents("t", events);
    const rule = { ...snapshot.decision_rule!, threshold: 0, comparator: "lt" as const };
    const base = { ...snapshot.flip!, baseline_result: { ...snapshot.flip!.baseline_result, estimate: -0.5 } };
    const crossing = { ...base, flipped_result: { ...base.flipped_result, estimate: 0.2 } };
    const { unmount } = render(
      <VerdictCard snapshot={{ ...snapshot, flip: { ...crossing, kind: "significance" }, decision_rule: rule }} />,
    );
    expect(document.querySelector(".vc-kind")?.getAttribute("data-kind")).toBe("significance");
    unmount();
    render(<VerdictCard snapshot={{ ...snapshot, flip: { ...crossing, kind: undefined }, decision_rule: rule }} />);
    expect(document.querySelector(".vc-kind")?.getAttribute("data-kind")).toBe("direction");
  });

  it("puts the robustness share first on the front face", () => {
    render(<VerdictCard snapshot={foldEvents("t", events)} />);
    const front = document.querySelector(".vc-face--front")!;
    expect(front.firstElementChild?.classList.contains("vc-robust")).toBe(true);
  });

  it("states the agreement share on the card from the report fields, also with the flip showing", () => {
    const snapshot = foldEvents("t", events);
    const report = { ...snapshot.report!, n_universes: 15, n_distinct_results: 10, robustness: 0.6, robustness_basis: "design_weighted" as const };
    render(<VerdictCard snapshot={{ ...snapshot, report }} />);
    expect(screen.getByTestId("vc-agree")).toHaveTextContent("60% of the analysis grid agrees");
    expect(screen.getByTestId("vc-agree-context")).toHaveTextContent("from 15 explored paths, 10 distinct results");
  });

  it("labels a non-grid share as the share of distinct explored results", () => {
    const snapshot = foldEvents("t", events);
    const report = { ...snapshot.report!, n_universes: 8, n_distinct_results: 8, robustness: 0.5, robustness_basis: "distinct_results" as const };
    render(<VerdictCard snapshot={{ ...snapshot, report }} />);
    expect(screen.getByTestId("vc-agree")).toHaveTextContent("50% of the distinct explored results agree");
    expect(screen.getByTestId("vc-agree")).not.toHaveTextContent("analysis grid");
  });

  it("shows no agreement line before the report", () => {
    render(<VerdictCard snapshot={until("stage", "baseline")} />);
    expect(screen.queryByTestId("vc-agree")).toBeNull();
  });
});
