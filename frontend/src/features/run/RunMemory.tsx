import type { MemoryUsed } from "../../shared/types/contracts";
import { AppLink, MEMORY_PATH, runPath } from "../../shared/router";
import { reusedSummary, reusedTotal } from "../memory/memoryFormat";
import "../memory/memory.css";

export function RunMemory({ memory }: { memory: MemoryUsed | null | undefined }) {
  const reused = reusedTotal(memory);
  if (!memory || reused === 0) return null;
  return (
    <section className="run-memory" aria-label="Memory">
      <h2 className="run-memory__title">Memory</h2>
      <p>
        This run reused <span className="mono">{reused}</span> {reused === 1 ? "memory" : "memories"} instead of asking
        a model again: {reusedSummary(memory)}. Each one was screened by Armor and re-validated before use.
      </p>
      <p>
        From{" "}
        {memory.sources.map((source, index) => (
          <span key={source.run_id}>
            {index > 0 && ", "}
            <AppLink to={runPath(source.run_id)} className="mono">
              {source.run_id}
            </AppLink>{" "}
            ({source.count})
          </span>
        ))}
        .{" "}
        <AppLink to={MEMORY_PATH} className="chip chip--link">
          Memory bank
        </AppLink>
      </p>
    </section>
  );
}
