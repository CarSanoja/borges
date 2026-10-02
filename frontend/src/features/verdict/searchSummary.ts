import type { SearchSummary } from "../../shared/types/contracts";

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function searchSentence(search: SearchSummary, flipFound: boolean): string {
  const scope = `within ${plural(search.universe_budget, "universe", "universes")}, ${plural(search.levels_explored, "level", "levels")}`;
  return flipFound ? `Smallest flip found ${scope}` : `No flip found ${scope}`;
}

export function searchBudgetNote(search: SearchSummary): string | null {
  if (!search.budget_exhausted) return null;
  return `The search budget ran out (${search.universes_used} of ${search.universe_budget} universes used), so a smaller flip may exist.`;
}
