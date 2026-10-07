import { describe, expect, it } from "vitest";
import { buildSampleRun } from "../../fixtures/sampleRun";
import type { AnalysisResult, RunSnapshot, Universe } from "../../shared/types/contracts";
import { foldEvents } from "../run/reducer";
import { agreementHeadline, isInconclusive, smallestP } from "./agreementHeadline";

const base = foldEvents("t", buildSampleRun("t"));
const rule = {
  ...base.decision_rule!,
  alpha: 0.05,
  positive_label: "FERTILITY SHIFTS RELIGIOSITY",
  negative_label: "NO CLEAR EVIDENCE",
};

function result(estimate: number, p: number): AnalysisResult {
  return { ...base.report!.original_result, estimate, p_value: p };
}

function universe(id: string, p: number, kind: Universe["kind"] = "single", status: Universe["status"] = "done"): Universe {
  return {
    ...Object.values(base.garden.universes)[0]!,
    id,
    kind,
    status,
    result: status === "done" ? result(0.3, p) : null,
  };
}

function fertility(overrides: Partial<NonNullable<RunSnapshot["report"]>> = {}): RunSnapshot {
  const universes = {
    a: universe("a", 0.82, "baseline"),
    b: universe("b", 0.41),
    c: universe("c", 0.07),
    v: universe("v", 0.001, "verification"),
    p: universe("p", 0.0001, "single", "pending"),
  };
  const report = {
    ...base.report!,
    original_verdict: "NO CLEAR EVIDENCE",
    original_result: result(0.28, 0.82),
    minimal_flip: null,
    n_universes: 32,
    n_flipped: 0,
    n_distinct_results: 32,
    ...overrides,
  };
  return { ...base, decision_rule: rule, flip: null, report, garden: { ...base.garden, universes } };
}

describe("isInconclusive", () => {
  it("requires the negative label and p at or above alpha", () => {
    expect(isInconclusive("NO CLEAR EVIDENCE", result(0.28, 0.82), rule)).toBe(true);
    expect(isInconclusive("NO CLEAR EVIDENCE", result(0.28, 0.05), rule)).toBe(true);
    expect(isInconclusive("NO CLEAR EVIDENCE", result(-2, 0.001), rule)).toBe(false);
    expect(isInconclusive("FERTILITY SHIFTS RELIGIOSITY", result(2, 0.9), rule)).toBe(false);
    expect(isInconclusive(null, result(0.28, 0.82), rule)).toBe(false);
    expect(isInconclusive("NO CLEAR EVIDENCE", null, rule)).toBe(false);
  });
});

describe("smallestP", () => {
  it("looks only at completed universes that are not verifications", () => {
    expect(smallestP(fertility().garden.universes)).toBe(0.07);
    expect(smallestP({})).toBeNull();
  });
});

describe("agreementHeadline", () => {
  it("calls fertility's paths inconclusive and gives the smallest p-value", () => {
    const headline = agreementHeadline(fertility())!;
    expect(headline).toMatchObject({ agree: 32, total: 32, inconclusive: true });
    expect(headline.pLine).toBe("No path reached p < 0.05; the smallest p-value was 0.070");
  });

  it("does not claim that no path reached alpha when one did", () => {
    const snapshot = fertility();
    snapshot.garden.universes.z = universe("z", 0.01);
    expect(agreementHeadline(snapshot)!.pLine).toBe("The smallest p-value was 0.010");
  });

  it("leads a positive original verdict with the grid share", () => {
    const snapshot = fertility({
      original_verdict: "FERTILITY SHIFTS RELIGIOSITY",
      original_result: result(1.2, 0.01),
      n_flipped: 5,
      n_universes: 12,
      n_distinct_results: 12,
    });
    expect(agreementHeadline(snapshot)).toMatchObject({ agree: 7, total: 12, inconclusive: false, label: "of the analysis grid agrees", pLine: null });
  });

  it("treats a significant negative verdict as conclusive", () => {
    const snapshot = fertility({ original_result: result(-1, 0.001) });
    expect(agreementHeadline(snapshot)).toMatchObject({ inconclusive: false, pLine: null });
  });

  it("gives the explored and distinct counts as context, as for teaching ratings", () => {
    const snapshot = fertility({
      original_verdict: "FERTILITY SHIFTS RELIGIOSITY",
      original_result: result(1.2, 0.01),
      n_universes: 20,
      n_distinct_results: 18,
    });
    expect(agreementHeadline(snapshot)).toMatchObject({ agree: 20, total: 20, context: "from 20 explored paths, 18 distinct results" });
  });

  it("counts every explored path as distinct when the distinct count is missing", () => {
    expect(agreementHeadline(fertility({ n_distinct_results: undefined }))!.context).toBe("from 32 explored paths, 32 distinct results");
  });

  it("returns nothing before the report", () => {
    expect(agreementHeadline({ ...fertility(), report: null })).toBeNull();
  });
});
