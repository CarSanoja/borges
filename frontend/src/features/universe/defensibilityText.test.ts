import { describe, expect, it } from "vitest";
import type { Option } from "../../shared/types/contracts";
import { defensibilityText } from "./StepDetailRow";

const base: Option = {
  id: "cluster_playershort",
  label: "Cluster the errors by playerShort",
  rationale: "Rows repeat players.",
  spec: "Binomial GLM, errors clustered by playerShort.",
  is_default: false,
  origin: "pinned",
  source: null,
  defensibility: null,
  code: null,
  cluster_by: "playerShort",
};

describe("defensibilityText", () => {
  it("says a seeded option was not judged by the model", () => {
    expect(defensibilityText(base)).toBe("seeded by Borges, not judged");
  });

  it("keeps the wording for planner and adversary options", () => {
    expect(defensibilityText({ ...base, origin: "planner" })).toBe("planner option, not judged");
    expect(defensibilityText({ ...base, origin: "adversary" })).toBe("not judged");
    expect(defensibilityText({ ...base, defensibility: 0.7 })).toBe("0.70 (judged)");
  });
});
