import type { SearchSummary } from "../../shared/types/contracts";
import { searchBudgetNote, searchSentence } from "./searchSummary";

interface Props {
  search: SearchSummary | null | undefined;
  flipFound: boolean;
  explored: number;
}

export function SearchNote({ search, flipFound, explored }: Props) {
  if (!search) return null;
  const budget = searchBudgetNote(search);
  return (
    <p className="vc-search" data-exhausted={search.budget_exhausted}>
      {searchSentence(search, flipFound, explored)}.
      {budget && <span className="vc-search__budget"> {budget}</span>}
    </p>
  );
}
