import type { AnalysisPlan } from "../../shared/types/contracts";
import { withPlanLabels } from "./planLabels";

interface Props {
  caveats: string[] | null | undefined;
  plan?: AnalysisPlan | null;
}

export function isArmorCaveat(text: string): boolean {
  return text.startsWith("Armor ");
}

export function RunCaveats({ caveats, plan = null }: Props) {
  if (!caveats || caveats.length === 0) return null;
  return (
    <section className="run-caveats" aria-label="Caveats">
      <h2 className="run-caveats__title">Caveats</h2>
      <ul>
        {caveats.map((text) => (
          <li key={text} data-armor={isArmorCaveat(text)}>
            {isArmorCaveat(text) && <span className="run-caveats__tag mono">armor</span>}
            {withPlanLabels(text, plan)}
          </li>
        ))}
      </ul>
    </section>
  );
}
