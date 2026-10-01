import { TONE_LABEL, TONE_VAR } from "./colors";
import type { Tone } from "./colors";

const ORDER: Tone[] = ["baseline", "agree", "flipped", "pending"];

export function Legend() {
  return (
    <ul className="garden-legend" aria-label="Legend">
      {ORDER.map((tone) => (
        <li key={tone}>
          <span className="garden-legend-dot" style={{ background: TONE_VAR[tone] }} />
          {TONE_LABEL[tone]}
        </li>
      ))}
    </ul>
  );
}
