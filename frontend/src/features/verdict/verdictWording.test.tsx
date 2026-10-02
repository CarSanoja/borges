import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { foldEvents } from "../run/reducer";
import { formatEstimate } from "./verdictFormat";
import { VerdictCard } from "./VerdictCard";

const snapshot = foldEvents("t", buildSampleRun("t"));

function withRule(threshold: number, kind: "direction" | "significance") {
  const rule = { ...snapshot.decision_rule!, threshold };
  const flip = { ...snapshot.flip!, kind };
  return { ...snapshot, decision_rule: rule, flip, report: null };
}

describe("verdict wording", () => {
  it("keeps the plus sign for differences and drops it for ratios", () => {
    expect(formatEstimate(0.012, 0)).toBe("+0.012");
    expect(formatEstimate(1.34, 1)).toBe("1.340");
    expect(formatEstimate(-0.4, 0)).toBe("-0.400");
  });

  it("prints a ratio estimate without a plus sign on the card", () => {
    const ratio = withRule(1, "direction");
    render(<VerdictCard snapshot={ratio} />);
    expect(document.body.textContent).not.toMatch(/\+\d/);
  });

  it("describes a significance flip as a changed verdict", () => {
    render(<VerdictCard snapshot={withRule(0, "significance")} />);
    expect(screen.getByText("One defensible change changes the verdict:")).toBeInTheDocument();
    expect(screen.queryByText(/reverses it/)).toBeNull();
    expect(screen.queryByText(/reverses this/)).toBeNull();
  });

  it("keeps reverses for a direction flip", () => {
    render(<VerdictCard snapshot={withRule(0, "direction")} />);
    expect(screen.getByText("One defensible change reverses it:")).toBeInTheDocument();
  });
});
