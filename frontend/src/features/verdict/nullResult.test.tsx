import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { RunSnapshot } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { VerdictCard } from "./VerdictCard";
import { nullResultSentence } from "./nullResult";

function nullRun(comparator: "gt" | "lt", nUniverses = 9): RunSnapshot {
  const snapshot = foldEvents("t", buildSampleRun("t"));
  const rule = { ...snapshot.decision_rule!, comparator };
  const report = snapshot.report!;
  return {
    ...snapshot,
    flip: null,
    decision_rule: rule,
    plan: snapshot.plan ? { ...snapshot.plan, decision_rule: rule } : null,
    report: {
      ...report,
      minimal_flip: null,
      n_universes: nUniverses,
      n_flipped: 0,
      original_verdict: rule.negative_label,
      original_result: { ...report.original_result, ci_low: -1.5, ci_high: 2.4 },
    },
  };
}

describe("null result sentence", () => {
  it("says what the data rule out from the upper end of the interval", () => {
    render(<VerdictCard snapshot={nullRun("gt")} />);
    expect(screen.getByTestId("vc-null")).toHaveTextContent(
      "The data rule out an effect above 2.400 (upper end of the 95% interval); every analysis path agreed there is no clear evidence, which is not proof of no effect.",
    );
  });

  it("uses the lower end when the rule looks below the threshold", () => {
    expect(nullResultSentence(nullRun("lt"))).toContain("rule out an effect below -1.500 (lower end");
  });

  it("is honest when only the default analysis ran", () => {
    expect(nullResultSentence(nullRun("gt", 1))).toContain("only the default analysis ran");
  });

  it("is absent for the positive verdict and when a flip exists", () => {
    const snapshot = foldEvents("t", buildSampleRun("t"));
    expect(nullResultSentence(snapshot)).toBeNull();
    const withFlip = { ...nullRun("gt"), flip: snapshot.flip };
    expect(nullResultSentence(withFlip)).toBeNull();
  });
});
