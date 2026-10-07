import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DecisionInfluence } from "../../shared/types/contracts";
import { InfluenceRow } from "./InfluenceRow";
import { describeShift, isImmaterialShift, NO_MATERIAL_EFFECT } from "./influenceMateriality";

const context = { largestShift: 0.5, baselineEstimate: 0.5286, flips: 0 };

function item(max_abs_delta: number, flips = 0): DecisionInfluence {
  return { step_id: "s", title: "Estimate conversion lift", mean_abs_delta: max_abs_delta, max_abs_delta, flips, n_alternatives: 2 };
}

describe("isImmaterialShift", () => {
  it("treats a shift below 1% of the largest shift as immaterial", () => {
    expect(isImmaterialShift(0.0000045, { ...context, baselineEstimate: null })).toBe(true);
    expect(isImmaterialShift(0.004, { ...context, baselineEstimate: null })).toBe(true);
    expect(isImmaterialShift(0.006, { ...context, baselineEstimate: null })).toBe(false);
  });

  it("treats a shift below 1% of the baseline estimate as immaterial", () => {
    expect(isImmaterialShift(0.0048, { largestShift: 0.2, baselineEstimate: 0.5286, flips: 0 })).toBe(true);
    expect(isImmaterialShift(0.006, { largestShift: 0.2, baselineEstimate: 0.5286, flips: 0 })).toBe(false);
  });

  it("never calls a shift that flips the verdict immaterial", () => {
    expect(isImmaterialShift(0.000001, { ...context, flips: 1 })).toBe(false);
  });
});

describe("describeShift", () => {
  it("says no material effect instead of a long decimal", () => {
    expect(describeShift(0.0000045, context)).toBe(NO_MATERIAL_EFFECT);
    expect(describeShift(0.0048, context)).toBe(NO_MATERIAL_EFFECT);
  });

  it("formats material values with sensible significant digits", () => {
    expect(describeShift(0.4521, context)).toBe("0.452");
    expect(describeShift(12.3456, { ...context, largestShift: 12.3456 })).toBe("12.35");
  });
});

describe("InfluenceRow", () => {
  it("renders no material effect for an immaterial row and the number for a material one", () => {
    const { unmount } = render(<ol><InfluenceRow item={item(0.0000045)} scale={0.5} baselineEstimate={0.5286} /></ol>);
    expect(screen.getByRole("listitem")).toHaveTextContent("no material effect");
    expect(screen.getByRole("listitem")).not.toHaveTextContent("0.0000045");
    unmount();
    render(<ol><InfluenceRow item={item(0.4521, 2)} scale={0.5} baselineEstimate={0.5286} /></ol>);
    expect(screen.getByRole("listitem")).toHaveTextContent("0.452");
    expect(screen.getByRole("listitem")).not.toHaveTextContent("no material effect");
  });
});
