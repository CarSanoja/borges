import { useEffect, useState } from "react";
import { ApiError, getCase } from "../../shared/api/client";
import type { CaseCard, RecordingSource } from "../../shared/types/contracts";
import { NeedsLive } from "../cases/NeedsLive";
import { useCases } from "../cases/useCases";
import { NotFound } from "../notfound/NotFound";
import { pickSource } from "../recording/recordingText";
import { RunPage } from "./RunPage";
import { prefersReducedMotion } from "./usePrefersReducedMotion";

export const INSTANT_SPEED = 100;
export const ANIMATED_SPEED = 8;
export const AUTOPLAY_LIMIT_MS = 4000;

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
  const [animated, setAnimated] = useState(() => !prefersReducedMotion());

  useEffect(() => {
    let active = true;
    setGate({ kind: "loading" });
    setAnimated(!prefersReducedMotion());
    getCase(caseId).then(
      (card) => active && setGate({ kind: "card", card }),
      (cause) => active && setGate({ kind: cause instanceof ApiError && cause.status === 404 ? "missing" : "unknown" }),
    );
    return () => {
      active = false;
    };
  }, [caseId]);

  useEffect(() => {
    if (!animated || gate.kind === "loading") return;
    const timer = setTimeout(() => setAnimated(false), AUTOPLAY_LIMIT_MS);
    return () => clearTimeout(timer);
  }, [animated, gate.kind]);

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
  const speed = animated ? ANIMATED_SPEED : INSTANT_SPEED;
  const replayControl = animated ? (
    <button type="button" className="btn replay-skip" onClick={() => setAnimated(false)}>
      Skip to the end
    </button>
  ) : prefersReducedMotion() ? null : (
    <button type="button" className="btn replay-animation" onClick={() => setAnimated(true)}>
      Replay the animation
    </button>
  );
  return (
    <RunPage
      source={{ kind: "replay", caseId, speed, recording }}
      onHome={onHome}
      replayControl={replayControl}
      holdVerdict={animated}
    />
  );
}
