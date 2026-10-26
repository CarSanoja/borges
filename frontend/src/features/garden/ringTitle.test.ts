import { describe, expect, it } from "vitest";
import { fitRingLabel, fitRingTitle, GLYPH_WIDTH, MAX_SQUEEZE, ringTitleCandidates } from "./ringTitle";

describe("ring titles", () => {
  it("drops leading verbs and falls back to the first noun", () => {
    expect(ringTitleCandidates("Choose which dyads to keep")).toEqual(["Choose which dyads to keep", "Dyads to keep", "Dyads"]);
    expect(ringTitleCandidates("Adjust for context")).toEqual(["Adjust for context", "Context"]);
  });

  it("keeps the full title when it fits and shortens before truncating", () => {
    expect(fitRingTitle("Fit the model", 20, 1.12)).toEqual({ text: "Fit the model", fits: true });
    expect(fitRingTitle("Choose which dyads to keep", 6, 1.12)).toEqual({ text: "Dyads", fits: true });
    expect(fitRingTitle("Choose which dyads to keep", 3, 1.12).fits).toBe(false);
  });

  it("never lays out an uppercase label wider than its arc", () => {
    const title = "Aggregate to user-level";
    for (const arc of [120, 160, 190, 220, 260]) {
      const label = fitRingLabel(title, arc);
      const natural = label.text.length * GLYPH_WIDTH;
      expect(natural <= arc || (label.textLength !== undefined && natural <= arc * MAX_SQUEEZE)).toBe(true);
    }
    expect(fitRingLabel(title, 160).text).toBe("Aggregate");
  });
});
