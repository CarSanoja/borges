import { describe, expect, it } from "vitest";
import { wrapLabel } from "./wrapLabel";

describe("wrapLabel", () => {
  it("keeps the whole metric across lines instead of cutting it at 34 characters", () => {
    const label = "odds ratio of a red card per game, dark vs light skin tone";
    const lines = wrapLabel(label, 25);
    expect(lines.length).toBeGreaterThan(1);
    expect(lines.join(" ")).toBe(label);
    expect(lines.every((line) => line.length <= 25)).toBe(true);
  });

  it("splits a single long word and marks real overflow with an ellipsis", () => {
    expect(wrapLabel("abcdefghij", 4, 5)).toEqual(["abcd", "efgh", "ij"]);
    const lines = wrapLabel("one two three four five six seven eight", 8, 2);
    expect(lines).toHaveLength(2);
    expect(lines[1]?.endsWith("…")).toBe(true);
  });
});
