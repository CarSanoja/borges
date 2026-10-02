import type { SearchSummary } from "../../shared/types/contracts";
import { searchBudgetNote, searchSentence } from "./searchSummary";

interface Props {
  search: SearchSummary | null | undefined;
  flipFound: boolean;
}

export function SearchNote({ search, flipFound }: Props) {
  if (!search) return null;
  const budget = searchBudgetNote(search);
  return (
    <p className="vc-search" data-exhausted={search.budget_exhausted}>
      {searchSentence(search, flipFound)}.
      {budget && <span className="vc-search__budget"> {budget}</span>}
    </p>
  );
}
