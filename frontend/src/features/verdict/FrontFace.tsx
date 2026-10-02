import type { RunSnapshot } from "../../shared/types/contracts";
import { effectRange } from "./flipKind";
import { ResultStats } from "./ResultStats";
import { Robustness } from "./Robustness";
import { activeFlip, activeRule, exploredCount, originalResult } from "./verdictModel";
import { ruleInWords } from "./verdictFormat";

interface Props {
  snapshot: RunSnapshot;
  verdict: string;
  hidden: boolean;
}

export function FrontFace({ snapshot, verdict, hidden }: Props) {
  const result = originalResult(snapshot);
  const rule = activeRule(snapshot);
  const flip = activeFlip(snapshot);
  const explored = exploredCount(snapshot);
  const clean = snapshot.status === "completed" && !flip;

  return (
    <div className="vc-face vc-face--front" aria-hidden={hidden} inert={hidden}>
      <span className="eyebrow">The original verdict</span>
      <h2 className="vc-verdict vc-verdict--gold">{verdict}</h2>
      {result && <ResultStats result={result} tone="gold" />}
      {rule && <p className="vc-rule">{ruleInWords(rule)}</p>}
      {flip && !hidden && <p className="vc-hint">Borges found a fork that reverses this.</p>}
      {clean && (
        <p className="vc-clean">
          No defensible flip found in {explored} {explored === 1 ? "universe" : "universes"}
        </p>
      )}
      {snapshot.report && <Robustness report={snapshot.report} range={effectRange(snapshot)} />}
    </div>
  );
}
