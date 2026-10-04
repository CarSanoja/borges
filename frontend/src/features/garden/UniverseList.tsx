import type { AnalysisPlan, Universe } from "../../shared/types/contracts";
import { universeAriaLabel } from "./labels";

interface Props {
  plan: AnalysisPlan | null;
  universes: Universe[];
  onSelect: (id: string) => void;
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

export function UniverseList({ plan, universes, onSelect }: Props) {
  return (
    <ul className="visually-hidden" aria-label="Universes">
      {universes.map((universe) => (
        <li key={universe.id}>
          <button type="button" onClick={() => onSelect(universe.id)}>
            Open {lowerFirst(universeAriaLabel(plan, universe))}
          </button>
        </li>
      ))}
    </ul>
  );
}
