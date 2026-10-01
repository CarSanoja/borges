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
    expect(screen.getByText(/explored universes agree/)).toBeInTheDocument();
  });

  it("reveals the flip with changes and the reproduced badge", () => {
    const snapshot = foldEvents("t", events);
    render(<VerdictCard snapshot={snapshot} />);
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
    expect(screen.getByText("No defensible flip found in 9 universes")).toBeInTheDocument();
    expect(screen.queryByText("One defensible change reverses it:")).not.toBeInTheDocument();
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
});
