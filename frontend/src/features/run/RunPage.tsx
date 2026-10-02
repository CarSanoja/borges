import { useState } from "react";
import type { MouseEvent } from "react";
import { Garden } from "../garden/Garden";
import { InfluenceBars } from "../influence/InfluenceBars";
import { SpecCurve } from "../speccurve/SpecCurve";
import { Telemetry } from "../telemetry/Telemetry";
import { UniverseDrawer } from "../universe/UniverseDrawer";
import { VerdictCard } from "../verdict/VerdictCard";
import { RecordingBanner } from "../recording/RecordingBanner";
import { AgentsUsed } from "./AgentsUsed";
import { RunCaveats } from "./RunCaveats";
import { RunMemory } from "./RunMemory";
import { RunHeader } from "./RunHeader";
import { useCaseCard } from "./useCaseCard";
import { NotFound } from "../notfound/NotFound";
import { CASE_GONE_MESSAGE, isNotFound, useRun, type RunSource } from "./useRun";
import "./run.css";
import "./runResponsive.css";
import "./skipLink.css";

interface Props {
  source: RunSource;
  onHome: () => void;
}

export function RunPage({ source, onHome }: Props) {
  const snapshot = useRun(source);
  const card = useCaseCard(source.kind === "replay" ? source.caseId : snapshot.case_id);
  const [selected, setSelected] = useState<string | null>(null);
  const runId = source.kind === "mock" ? null : snapshot.run_id;

  if (isNotFound(snapshot)) {
    const isCase = snapshot.error === CASE_GONE_MESSAGE;
    return (
      <NotFound
        title={isCase ? "Case not found" : "Run not found"}
        message={
          isCase
            ? "No case with that id exists on this server. The recorded runs below are always available."
            : "This run does not exist on this server. Runs are cleared on redeploy; the recorded runs below are always available."
        }
      />
    );
  }

  const skipToVerdict = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    document.getElementById("verdict")?.focus();
  };

  return (
    <main className="run-page">
      <a className="skip-link" href="#verdict" onClick={skipToVerdict}>
        Skip to verdict
      </a>
      <RunHeader snapshot={snapshot} onHome={onHome} traceRunId={runId} />
      {source.kind === "replay" && source.recording && (
        <RecordingBanner
          caseId={source.caseId}
          source={source.recording}
          live={card?.live_recording}
          hasScripted={card?.has_recording ?? true}
        />
      )}
      {snapshot.error && (
        <p className="run-error" role="alert">
          {snapshot.error}
        </p>
      )}
      <section className="run-hero" aria-label="Garden and verdict">
        <div className="run-garden">
          <Garden snapshot={snapshot} selectedUniverseId={selected} onSelectUniverse={setSelected} />
        </div>
        <aside className="run-side" id="verdict" tabIndex={-1} aria-label="Verdict panel">
          <VerdictCard snapshot={snapshot} />
        </aside>
      </section>
      <section className="run-below" aria-label="Evidence">
        <div className="run-curve">
          <SpecCurve
            snapshot={snapshot}
            reference={card?.reference}
            referenceLabel={card?.reference_label}
            selectedUniverseId={selected}
            onSelectUniverse={setSelected}
          />
        </div>
        <div className="run-influence">
          <InfluenceBars snapshot={snapshot} />
        </div>
      </section>
      <RunCaveats caveats={snapshot.report?.caveats} />
      <RunMemory memory={snapshot.memory} />
      <footer className="run-footer">
        <AgentsUsed agents={snapshot.agents ?? snapshot.report?.agents} />
        <Telemetry snapshot={snapshot} />
      </footer>
      <UniverseDrawer
        runId={runId}
        snapshot={snapshot}
        universeId={selected}
        onClose={() => setSelected(null)}
      />
    </main>
  );
}
