import type { SearchSummary } from "../../shared/types/contracts";

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function searchSentence(search: SearchSummary, flipFound: boolean, explored: number): string {
  const scope = `${explored} explored of a ${search.universe_budget}-universe budget, ${plural(search.levels_explored, "level", "levels")}`;
  return flipFound ? `Smallest flip found: ${scope}` : `No flip found: ${scope}`;
}

export function searchBudgetNote(search: SearchSummary): string | null {
  if (!search.budget_exhausted) return null;
  return `The ${search.universe_budget}-universe budget ran out, so a smaller flip may exist.`;
}
