import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import { FailurePanel } from "./FailurePanel";
import { foldEvents } from "./reducer";

const RAW =
  "LLMError: no option passed its smoke run\nTraceback (most recent call last):\nIndexError: index 1 is out of bounds\nAttributeError: LogitResults has no attribute get_robustcov_results";

function failed() {
  const snapshot = foldEvents("t", buildSampleRun("t").slice(0, 6));
  return { ...snapshot, status: "failed" as const, error: RAW, usage: { ...snapshot.usage, cost_usd: 0.1234 } };
}

describe("FailurePanel", () => {
  it("summarises the failure in plain words with cost and a suggestion", () => {
    render(<FailurePanel snapshot={failed()} />);
    const panel = screen.getByTestId("failure-panel");
    expect(panel).toHaveTextContent("This run could not finish");
    expect(panel).toHaveTextContent(/The run stopped (at the stage|before the first stage)/);
    expect(panel).toHaveTextContent("Nothing was concluded");
    expect(panel).toHaveTextContent("$0.1234");
    expect(panel).toHaveTextContent(/simplifying the question/);
  });

  it("names a column the question needs that the data does not have", () => {
    const error =
      "LLMError: step s1: no option passed its smoke run; last error: KeyError: \"'smoking' column required but not found\" | columns available (4): ['age', 'bmi', 'exercise_hours', 'lung_disease']; ctx keys: []";
    render(<FailurePanel snapshot={{ ...failed(), error }} />);
    const panel = screen.getByTestId("failure-panel");
    expect(panel).toHaveTextContent('The data has no column "smoking"');
    expect(panel).toHaveTextContent("columns: age, bmi, exercise_hours, lung_disease");
    expect(panel).toHaveTextContent(/does not build a stand-in/);
  });

  it("keeps the raw error behind a collapsed disclosure", () => {
    render(<FailurePanel snapshot={failed()} />);
    const details = screen.getByText("Technical details").closest("details")!;
    expect(details.open).toBe(false);
    expect(details).toHaveTextContent("LogitResults has no attribute get_robustcov_results");
    expect(screen.getByTestId("failure-panel").querySelector("p")?.textContent).not.toContain("Traceback");
  });
});
