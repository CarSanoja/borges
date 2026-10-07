import type { SearchSummary } from "../../shared/types/contracts";

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function searchSentence(search: SearchSummary, flipFound: boolean, explored: number): string {
  const scope = `${plural(explored, "universe", "universes")} explored out of a limit of ${search.universe_budget}, in ${plural(search.levels_explored, "round", "rounds")} of combining choices`;
  return flipFound ? `Smallest flip found: ${scope}` : `No flip found: ${scope}`;
}

export function searchBudgetNote(search: SearchSummary): string | null {
  if (!search.budget_exhausted) return null;
  return `The limit of ${search.universe_budget} universes was reached, so a smaller flip may exist.`;
}
