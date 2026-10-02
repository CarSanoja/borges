import type { RunSnapshot } from "../../shared/types/contracts";
import { Counter } from "./Counter";
import { codingSentence } from "./codingSummary";
import { StageTimeline } from "./StageTimeline";
import { formatCost, formatCount, formatTokens } from "./telemetryFormat";
import "./telemetry.css";

interface Props {
  snapshot: RunSnapshot;
}

export function Telemetry({ snapshot }: Props) {
  const { usage } = snapshot;
  const coding = snapshot.report?.coding;
  const tokens = usage.tokens_in + usage.tokens_out;
  return (
    <section aria-label="Telemetry" className="tm">
      <div className="tm-counters">
        <Counter value={usage.universes} label={usage.universes === 1 ? "universe" : "universes"} format={formatCount} />
        <Counter value={usage.checkpoints} label={usage.checkpoints === 1 ? "sandbox checkpoint" : "sandbox checkpoints"} format={formatCount} />
        {snapshot.llm === "scripted" ? (
          <p className="tm-scripted">scripted, no model calls</p>
        ) : (
          <>
            <Counter
              value={usage.llm_calls}
              label={usage.llm_calls === 1 ? "LLM call" : "LLM calls"}
              format={formatCount}
              note={usage.cached_calls > 0 ? `${formatCount(usage.cached_calls)} cached` : undefined}
            />
            <Counter
              value={tokens}
              label="tokens"
              format={formatTokens}
              title={`${formatCount(usage.tokens_in)} in, ${formatCount(usage.tokens_out)} out`}
            />
            <Counter value={usage.cost_usd} label="USD" format={formatCost} />
          </>
        )}
      </div>
      {coding && <p className="tm-coding">{codingSentence(coding)}</p>}
      <StageTimeline snapshot={snapshot} />
    </section>
  );
}
