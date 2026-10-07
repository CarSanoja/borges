import { describe, expect, it } from "vitest";
import type { SearchSummary } from "../../shared/types/contracts";
import { searchBudgetNote, searchSentence } from "./searchSummary";

const search: SearchSummary = {
  levels_explored: 3,
  max_combinations_per_level: 5,
  universe_budget: 40,
  universes_used: 40,
  budget_exhausted: true,
};

describe("searchSummary", () => {
  it("states the numbers in plain words", () => {
    expect(searchSentence(search, true, 32)).toBe(
      "Smallest flip found: 32 universes explored out of a limit of 40, in 3 rounds of combining choices",
    );
    expect(searchSentence({ ...search, levels_explored: 1 }, false, 1)).toBe(
      "No flip found: 1 universe explored out of a limit of 40, in 1 round of combining choices",
    );
  });

  it("explains an exhausted limit without the word budget", () => {
    expect(searchBudgetNote(search)).toBe("The limit of 40 universes was reached, so a smaller flip may exist.");
    expect(searchBudgetNote({ ...search, budget_exhausted: false })).toBeNull();
  });
});
