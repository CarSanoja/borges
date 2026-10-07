import { useState } from "react";
import type { Option, UniverseStepDetail } from "../../shared/types/contracts";
import { CodeBlock } from "./CodeBlock";

export function defensibilityText(option: Option): string {
  if (option.defensibility !== null) return `${option.defensibility.toFixed(2)} (judged)`;
  if (option.origin === "pinned") return "seeded by Borges, not judged";
  return option.origin === "adversary" ? "not judged" : "planner option, not judged";
}

function rows(value: number): string {
  return value.toLocaleString("en-US");
}

export function clusterLine(option: Option): string | null {
  if (!option.cluster_by) return null;
  return `Errors clustered by ${option.cluster_by}: the harness fits the model with cluster-robust errors on that column, overriding the covariance the code asks for.`;
}

export function StepDetailRow({ detail, index }: { detail: UniverseStepDetail; index: number }) {
  const { step, option, trace, changed, checkpoint_id } = detail;
  const [showCode, setShowCode] = useState(false);
  const cluster = clusterLine(option);
  const codeId = `u-code-${step.id}`;
  return (
    <li className={`u-step${changed ? " is-changed" : ""}`} data-changed={changed}>
      <div className="u-step-head">
        <span className="u-step-n mono">{index + 1}</span>
        <div>
          <p className="eyebrow">{step.title}</p>
          <h4 className="u-step-option">{option.label}</h4>
        </div>
        {changed && <span className="u-tag">differs from default</span>}
      </div>
      <p className="u-rationale">{option.rationale}</p>
      {cluster && <p className="u-cluster">{cluster}</p>}
      <dl className="u-facts">
        <div>
          <dt>Defensibility</dt>
          <dd className="mono">{defensibilityText(option)}</dd>
        </div>
        <div>
          <dt>Proposed by</dt>
          <dd>{option.origin}</dd>
        </div>
        {option.source && (
          <div>
            <dt>Cited by the model, not checked</dt>
            <dd>{option.source}</dd>
          </div>
        )}
        {trace && (
          <div>
            <dt>Rows</dt>
            <dd className="mono">
              {rows(trace.rows_before)} → {rows(trace.rows_after)}
            </dd>
          </div>
        )}
        {checkpoint_id && (
          <div>
            <dt>Checkpoint</dt>
            <dd className="mono">{checkpoint_id}</dd>
          </div>
        )}
      </dl>
      {option.code ? (
        <>
          <button
            type="button"
            className="u-code-toggle"
            aria-expanded={showCode}
            aria-controls={codeId}
            onClick={() => setShowCode((value) => !value)}
          >
            {showCode ? "Hide code" : "Show code"}
          </button>
          {showCode && (
            <div id={codeId}>
              <CodeBlock code={option.code} label={`Code for ${option.label}`} />
            </div>
          )}
        </>
      ) : (
        <p className="u-nocode">No code recorded for this option.</p>
      )}
    </li>
  );
}
