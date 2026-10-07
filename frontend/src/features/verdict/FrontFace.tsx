import type { RunSnapshot } from "../../shared/types/contracts";
import { effectRange } from "./flipKind";
import { isInconclusive } from "./agreementHeadline";
import { SearchNote } from "./SearchNote";
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
  const done = snapshot.status === "completed" && !flip;
  const untested = done && (snapshot.report?.n_universes ?? 0) <= 1;
  const clean = done && !untested;

  return (
    <div className="vc-face vc-face--front" aria-hidden={hidden} inert={hidden}>
      {snapshot.report && (
        <Robustness
          report={snapshot.report}
          range={effectRange(snapshot)}
          plan={snapshot.plan}
          inconclusive={isInconclusive(verdict, result, rule)}
        />
      )}
      <span className="eyebrow">The original verdict</span>
      <h2 className="vc-verdict vc-verdict--gold">{verdict}</h2>
      {result && <ResultStats result={result} tone="gold" threshold={rule?.threshold ?? 0} />}
      {rule && <p className="vc-rule">{ruleInWords(rule)}</p>}
      {flip && !hidden && <p className="vc-hint">Borges found a fork that changes this verdict.</p>}
      {clean && <p className="vc-clean">No defensible flip found</p>}
      {untested && (
        <p className="vc-clean vc-clean--untested" data-testid="untested">
          Not tested: only the default analysis ran
        </p>
      )}
      {!flip && <SearchNote search={snapshot.report?.search} flipFound={false} explored={explored} />}
    </div>
  );
}
