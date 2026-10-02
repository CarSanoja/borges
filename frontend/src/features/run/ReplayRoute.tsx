import { useEffect, useState } from "react";
import { ApiError, getCase } from "../../shared/api/client";
import type { CaseCard, RecordingSource } from "../../shared/types/contracts";
import { NeedsLive } from "../cases/NeedsLive";
import { useCases } from "../cases/useCases";
import { NotFound } from "../notfound/NotFound";
import { pickSource } from "../recording/recordingText";
import { RunPage } from "./RunPage";

type Gate =
  | { kind: "loading" }
  | { kind: "card"; card: CaseCard }
  | { kind: "missing" }
  | { kind: "unknown" };

interface Props {
  caseId: string;
  requested?: RecordingSource | null;
  onHome: () => void;
}

export function ReplayRoute({ caseId, requested = null, onHome }: Props) {
  const [gate, setGate] = useState<Gate>({ kind: "loading" });
  const { cases } = useCases();

  useEffect(() => {
    let active = true;
    setGate({ kind: "loading" });
    getCase(caseId).then(
      (card) => active && setGate({ kind: "card", card }),
      (cause) => active && setGate({ kind: cause instanceof ApiError && cause.status === 404 ? "missing" : "unknown" }),
    );
    return () => {
      active = false;
    };
  }, [caseId]);

  if (gate.kind === "loading") {
    return (
      <main className="run-page">
        <p role="status" className="eyebrow">
          Opening the case
        </p>
      </main>
    );
  }
  if (gate.kind === "missing") {
    return (
      <NotFound
        title="Case not found"
        message="No case with that id exists on this server. The recorded runs below are always available."
      />
    );
  }
  if (gate.kind === "card" && !gate.card.has_recording && !gate.card.live_recording) {
    return <NeedsLive card={gate.card} recorded={cases.filter((item) => item.has_recording || item.live_recording)} />;
  }
  const live = gate.kind === "card" ? gate.card.live_recording : null;
  const scripted = gate.kind === "card" ? gate.card.has_recording : true;
  const recording = gate.kind === "card" ? pickSource(requested, live, scripted) : undefined;
  return <RunPage source={{ kind: "replay", caseId, speed: 1, recording }} onHome={onHome} />;
}
