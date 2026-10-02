import { AppLink, runPath } from "../../shared/router";
import { ChainBadge } from "./ChainBadge";
import { SpanTree } from "./SpanTree";
import { TraceSummary } from "./TraceSummary";
import { useTrace } from "./useTrace";
import "./trace.css";

interface Props {
  runId: string;
}

export function TracePage({ runId }: Props) {
  const state = useTrace(runId);
  return (
    <main className="trace-page">
      <header className="trace-header">
        <AppLink to="/" className="run-home">
          Borges
        </AppLink>
        <div className="trace-header__body">
          <p className="eyebrow">Reasoning chain trace</p>
          <h1 className="trace-title mono">{runId}</h1>
        </div>
        <div className="trace-header__meta">
          {state.status === "ready" && <ChainBadge chain={state.trace.audit_chain} />}
          <AppLink to={runPath(runId)} className="chip chip--link">
            Back to the run
          </AppLink>
        </div>
      </header>
      {state.status === "loading" && <p className="trace-note" role="status">Reading the trace</p>}
      {state.status === "error" && (
        <p className="run-error" role="alert">
          {state.message}
        </p>
      )}
      {state.status === "ready" && state.trace.roots.length === 0 && (
        <p className="trace-note" data-testid="trace-empty">
          {state.trace.reason ?? "This run has no spans."}
        </p>
      )}
      {state.status === "ready" && state.trace.roots.length > 0 && (
        <>
          <TraceSummary trace={state.trace} />
          <SpanTree roots={state.trace.roots} />
        </>
      )}
    </main>
  );
}
