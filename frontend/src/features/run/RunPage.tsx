import { useState } from "react";
import { Garden } from "../garden/Garden";
import { InfluenceBars } from "../influence/InfluenceBars";
import { SpecCurve } from "../speccurve/SpecCurve";
import { Telemetry } from "../telemetry/Telemetry";
import { UniverseDrawer } from "../universe/UniverseDrawer";
import { VerdictCard } from "../verdict/VerdictCard";
import { RunHeader } from "./RunHeader";
import { useCaseCard } from "./useCaseCard";
import { useRun, type RunSource } from "./useRun";
import "./run.css";

interface Props {
  source: RunSource;
  onHome: () => void;
}

export function RunPage({ source, onHome }: Props) {
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
        </p>
      )}
      <div className="run-grid">
        <div className="run-garden">
          <Garden snapshot={snapshot} selectedUniverseId={selected} onSelectUniverse={setSelected} />
        </div>
        <aside className="run-side">
          <VerdictCard snapshot={snapshot} />
          <InfluenceBars snapshot={snapshot} />
        </aside>
        <div className="run-curve">
          <SpecCurve
            snapshot={snapshot}
            reference={card?.reference}
            referenceLabel={card?.reference_label}
            selectedUniverseId={selected}
            onSelectUniverse={setSelected}
          />
        </div>
      </div>
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
