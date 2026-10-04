import { describe, expect, it } from "vitest";
import { SAMPLE_STEPS } from "../../fixtures/samplePlan";
import type { AnalysisPlan } from "../../shared/types/contracts";
import { withPlanLabels } from "./planLabels";

const base = { steps: SAMPLE_STEPS } as AnalysisPlan;

describe("withPlanLabels", () => {
  it("replaces step and option ids with their titles and labels", () => {
    const step = SAMPLE_STEPS[0]!;
    const option = step.options[0]!;
    const plan = { ...base, steps: [{ ...step, id: "step_model", title: "Statistical model", options: [{ ...option, id: "model_ols_clustered", label: "OLS clustered" }] }] };
    expect(withPlanLabels("Every option of step step_model failed (model_ols_clustered).", plan)).toBe(
      "Every option of step Statistical model failed (OLS clustered).",
    );
  });

  it("leaves unknown ids, plain words and a missing plan untouched", () => {
    expect(withPlanLabels("step_unknown stays", base)).toBe("step_unknown stays");
    expect(withPlanLabels("step_model stays", null)).toBe("step_model stays");
  });
});
