import { AppLink } from "../../shared/router";
import { useMe } from "../identity/useMe";
import { ForgetButton } from "./ForgetButton";
import { MemoryTable } from "./MemoryTable";
import { modeText, totalCount } from "./memoryFormat";
import { useMemory } from "./useMemory";
import "../trace/trace.css";
import "./memory.css";

export function MemoryPage() {
  const [state, forget] = useMemory();
  const [me] = useMe();
  const scopes = me.status === "ready" ? me.me.scopes : [];
  const canForget = scopes.includes("memory:write") || scopes.includes("admin");
  return (
    <main className="memory-page">
      <header className="trace-header">
        <AppLink to="/" className="run-home">
          Borges
        </AppLink>
        <div className="trace-header__body">
          <p className="eyebrow">Long-term memory</p>
          <h1 className="trace-title">Memory</h1>
        </div>
      </header>
      {state.status === "loading" && <p className="trace-note" role="status">Reading the memory bank</p>}
      {state.status === "error" && <p className="run-error" role="alert">{state.message}</p>}
      {state.status === "ready" && (
        <>
          <p className="memory-mode" data-enabled={state.summary.enabled} data-mode={state.summary.mode}>
            {modeText(state.summary)}
          </p>
          <p className="memory-total">
            <span className="mono">{totalCount(state.summary)}</span> memories for{" "}
            <span className="mono">{state.summary.tenant}</span>
          </p>
          <MemoryTable summary={state.summary} canForget={canForget} onForget={forget} />
          {canForget && totalCount(state.summary) > 0 && (
            <ForgetButton label="Forget everything" onConfirm={() => forget()} />
          )}
          {!canForget && (
            <p className="memory-hint">Erasing memories needs an API key with the memory:write scope.</p>
          )}
        </>
      )}
    </main>
  );
}
