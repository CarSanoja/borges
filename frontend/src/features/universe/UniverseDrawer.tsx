import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect } from "react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { CopyButton } from "./CopyButton";
import { StepDetailRow } from "./StepDetailRow";
import { useUniverseDetail } from "./useUniverseDetail";
import "./universe.css";
import "./universeCode.css";

interface Props {
  runId: string | null;
  snapshot: RunSnapshot;
  universeId: string | null;
  onClose: () => void;
}

export function UniverseDrawer({ runId, snapshot, universeId, onClose }: Props) {
  const reduced = useReducedMotion();
  const detail = useUniverseDetail(runId, snapshot, universeId);
  const open = detail !== null;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const universe = detail?.universe;
  const result = universe?.result;
  const verified = Boolean(
    universe && snapshot.flip && snapshot.flip.universe_id === universe.id && snapshot.flip.reproduced,
  );
  const flipped = universe?.flipped === true;

  return (
    <AnimatePresence>
      {detail && universe && (
        <motion.aside
          key="universe-drawer"
          className="u-drawer"
          aria-label="Universe"
          data-run={runId ?? ""}
          initial={reduced ? { opacity: 0 } : { x: "100%" }}
          animate={reduced ? { opacity: 1 } : { x: 0 }}
          exit={reduced ? { opacity: 0 } : { x: "100%" }}
          transition={{ duration: reduced ? 0 : 0.34, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="u-head">
            <div>
              <p className="eyebrow">Universe · {universe.kind}</p>
              <h3 className="u-id mono">{universe.id}</h3>
            </div>
            <button type="button" className="u-close" aria-label="Close" onClick={onClose}>
              Close
            </button>
          </header>
          <div className="u-summary">
            <span className={`u-verdict ${flipped ? "is-flip" : "is-agree"}`}>
              {universe.verdict ?? universe.status}
            </span>
            {verified && <span className="u-badge">Reproduced from scratch</span>}
            {result && (
              <p className="mono u-result">
                {result.metric || snapshot.decision_rule?.metric} {result.estimate.toFixed(3)} [{result.ci_low.toFixed(3)}, {result.ci_high.toFixed(3)}] · p=
                {result.p_value.toPrecision(2)} · n={result.n.toLocaleString("en-US")}
              </p>
            )}
            {universe.error && <p className="case-error">{universe.error}</p>}
          </div>
          <ol className="u-steps">
            {detail.steps.map((stepDetail, index) => (
              <StepDetailRow key={stepDetail.step.id} detail={stepDetail} index={index} />
            ))}
          </ol>
          <footer className="u-repro">
            <p className="eyebrow">Reproduce</p>
            <div className="u-repro-row">
              <code className="mono">{detail.reproduce_command}</code>
              <CopyButton text={detail.reproduce_command} />
            </div>
          </footer>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
