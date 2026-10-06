import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { VerdictCard } from "./VerdictCard";

const snapshot = foldEvents("t", buildSampleRun("t"));

function withReport(extra: Record<string, unknown>) {
  return { ...snapshot, report: { ...snapshot.report!, ...extra } };
}

describe("robustness rating", () => {
  it("says how few universes there are when the rating is null", () => {
    const report = withReport({ robustness_rating: null, n_universes: 5 });
    render(<VerdictCard snapshot={report} />);
    expect(screen.getByText(/^Too few distinct paths \(5\) to rate robustness$/)).toBeInTheDocument();
    expect(document.querySelector(".vc-robust__fill")).toBeNull();
  });

  it("shows the reason the statistics layer gave", () => {
    render(<VerdictCard snapshot={withReport({ robustness_rating: null, robustness_rating_reason: "below 10 universes" })} />);
    expect(screen.getByText("below 10 universes")).toBeInTheDocument();
  });

  it("shows the rating as a percentage when there is one", () => {
    render(<VerdictCard snapshot={withReport({ robustness_rating: 0.8, robustness: 0.5 })} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("falls back to the plain robustness when the field is absent", () => {
    render(<VerdictCard snapshot={withReport({ robustness: 0.6 })} />);
    expect(screen.getByText("60%")).toBeInTheDocument();
  });
});

describe("flip honesty notes", () => {
  it("flags a contaminated flip and an estimand change on the flipped side", () => {
    const flip = { ...snapshot.flip!, contaminated: true, estimand_change: "adds 40 covariates" };
    render(<VerdictCard snapshot={{ ...snapshot, flip }} />);
    expect(screen.getByTestId("flip-contaminated")).toHaveTextContent("Contaminated analysis flip");
    expect(screen.getByTestId("flip-estimand")).toHaveTextContent("adds 40 covariates");
  });

  it("shows neither note on an ordinary flip", () => {
    render(<VerdictCard snapshot={snapshot} />);
    expect(screen.queryByTestId("flip-contaminated")).toBeNull();
    expect(screen.queryByTestId("flip-estimand")).toBeNull();
  });
});
