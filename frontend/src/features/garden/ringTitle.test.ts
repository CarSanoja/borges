import { describe, expect, it } from "vitest";
import { fitRingTitle, ringTitleCandidates } from "./ringTitle";

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
});
