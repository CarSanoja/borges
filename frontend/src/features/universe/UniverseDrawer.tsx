import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { RunSnapshot } from "../../shared/types/contracts";
import { formatP } from "../verdict/verdictFormat";
import { ReproduceBlock } from "./ReproduceBlock";
import { StepDetailRow } from "./StepDetailRow";
import { useDialogFocus } from "./useDialogFocus";
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

  const dialogRef = useDialogFocus(open, onClose);

  const universe = detail?.universe;
  const result = universe?.result;
  const verified = Boolean(
    universe && snapshot.flip && snapshot.flip.universe_id === universe.id && snapshot.flip.reproduced,
  );
  const flipped = universe?.flipped === true;

  return (
    <AnimatePresence>
      {detail && universe && (
        <motion.div
          key="universe-drawer"
          ref={dialogRef}
          className="u-drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="u-drawer-title"
          tabIndex={-1}
          data-run={runId ?? ""}
          initial={reduced ? { opacity: 0 } : { x: "100%" }}
          animate={reduced ? { opacity: 1 } : { x: 0 }}
          exit={reduced ? { opacity: 0 } : { x: "100%" }}
          transition={{ duration: reduced ? 0 : 0.34, ease: [0.22, 1, 0.36, 1] }}
        >
          <header className="u-head">
            <div>
              <p className="eyebrow">Universe · {universe.kind}</p>
              <h3 id="u-drawer-title" className="u-id mono">{universe.id}</h3>
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
                {result.metric || snapshot.decision_rule?.metric} {result.estimate.toFixed(3)} [{result.ci_low.toFixed(3)}, {result.ci_high.toFixed(3)}] · p{" "}
                {formatP(result.p_value).startsWith("<") ? "" : "= "}
                {formatP(result.p_value)} · n={result.n.toLocaleString("en-US")}
              </p>
            )}
            {universe.error && <p className="case-error">{universe.error}</p>}
          </div>
          <ol className="u-steps">
            {detail.steps.map((stepDetail, index) => (
              <StepDetailRow key={stepDetail.step.id} detail={stepDetail} index={index} />
            ))}
          </ol>
          <ReproduceBlock detail={detail} hasRun={runId !== null} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
