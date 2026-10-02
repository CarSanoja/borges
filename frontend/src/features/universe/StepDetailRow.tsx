import type { Option, UniverseStepDetail } from "../../shared/types/contracts";
import { CodeBlock } from "./CodeBlock";

export function defensibilityText(option: Option): string {
  if (option.defensibility !== null) return `${option.defensibility.toFixed(2)} (judged)`;
  return option.origin === "adversary" ? "not judged" : "planner option, not judged";
}

function rows(value: number): string {
  return value.toLocaleString("en-US");
}

export function StepDetailRow({ detail, index }: { detail: UniverseStepDetail; index: number }) {
  const { step, option, trace, changed, checkpoint_id } = detail;
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
      <dl className="u-facts">
        <div>
          <dt>Defensibility</dt>
          <dd className="mono">{defensibilityText(option)}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{option.source ?? option.origin}</dd>
        </div>
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
        <CodeBlock code={option.code} label={`Code for ${option.label}`} />
      ) : (
        <p className="u-nocode">No code recorded for this option.</p>
      )}
    </li>
  );
}
