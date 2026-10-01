import { useState } from "react";
import { Garden } from "../garden/Garden";
import { InfluenceBars } from "../influence/InfluenceBars";
import { SpecCurve } from "../speccurve/SpecCurve";
import { Telemetry } from "../telemetry/Telemetry";
import { UniverseDrawer } from "../universe/UniverseDrawer";
import { VerdictCard } from "../verdict/VerdictCard";
import { RunHeader } from "./RunHeader";
import { useCaseCard } from "./useCaseCard";
import { RUN_GONE_MESSAGE, useRun, type RunSource } from "./useRun";
import "./run.css";
import "./runResponsive.css";

interface Props {
  source: RunSource;
  onHome: () => void;
  onOpenReplay?: (caseId: string) => void;
}

export function RunPage({ source, onHome, onOpenReplay }: Props) {
  const snapshot = useRun(source);
  const card = useCaseCard(snapshot.case_id);
  const [selected, setSelected] = useState<string | null>(null);
  const runId = source.kind === "mock" ? null : snapshot.run_id;

  return (
    <div className="run-page">
      <RunHeader snapshot={snapshot} onHome={onHome} />
      {snapshot.error && (
        <p className="run-error" role="alert">
          {snapshot.error}
          {snapshot.error === RUN_GONE_MESSAGE && snapshot.case_id && onOpenReplay && (
            <>
              {" "}
              <button type="button" className="link-btn" onClick={() => onOpenReplay(snapshot.case_id ?? "")}>
                Watch the recorded run
              </button>
            </>
          )}
        </p>
      )}
      <section className="run-hero" aria-label="Garden and verdict">
        <div className="run-garden">
          <Garden snapshot={snapshot} selectedUniverseId={selected} onSelectUniverse={setSelected} />
        </div>
        <aside className="run-side">
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
      <footer className="run-footer">
        <Telemetry snapshot={snapshot} />
      </footer>
      <UniverseDrawer
        runId={runId}
        snapshot={snapshot}
        universeId={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
