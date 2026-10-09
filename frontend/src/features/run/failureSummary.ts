import type { RunSnapshot } from "../../shared/types/contracts";
import { currentStage, stageLabel } from "./runLabels";

export interface FailureSummary {
  sentence: string;
  suggestion: string;
}

function failedStep(snapshot: RunSnapshot): string | null {
  const error = (snapshot.error ?? "").toLowerCase();
  const step = snapshot.plan?.steps.find(
    (s) => error.includes(s.id.toLowerCase()) || error.includes(s.title.toLowerCase()),
  );
  return step ? step.title : null;
}

const MISSING_KEY = /KeyError: "?'([^'"]+)'/;
const AVAILABLE = /columns available \(\d+\): \[([^\]]*)\]/;

export function missingColumn(error: string): { column: string; available: string[] } | null {
  const key = MISSING_KEY.exec(error);
  const listed = AVAILABLE.exec(error);
  const named = key?.[1];
  const list = listed?.[1];
  if (named === undefined || list === undefined) return null;
  const available = [...list.matchAll(/'([^']+)'/g)].flatMap((m) => (m[1] ? [m[1]] : []));
  const column = named.replace(/ column required but not found$/, "");
  return available.includes(column) ? null : { column, available };
}

function suggestionFor(snapshot: RunSnapshot): string {
  const error = snapshot.error ?? "";
  if (/smoke run|LogitResults|IndexError|AttributeError/.test(error)) {
    return "Try simplifying the question, or check that the outcome column holds the values you expect.";
  }
  return "Try again, simplify the question, or check the outcome column and the data you uploaded.";
}

export function failureSummary(snapshot: RunSnapshot): FailureSummary {
  const missing = missingColumn(snapshot.error ?? "");
  if (missing) {
    return {
      sentence: `The data has no column "${missing.column}", which this analysis needs (columns: ${missing.available.join(", ")}).`,
      suggestion:
        "Borges does not build a stand-in for a missing column from the others. Upload a file that has it, or ask a question these columns can answer.",
    };
  }
  const stage = currentStage(snapshot);
  const step = failedStep(snapshot);
  const where = stage ? `at the stage "${stageLabel(stage)}"` : "before the first stage";
  const at = step ? `, at the step "${step}"` : "";
  return {
    sentence: `The run stopped ${where}${at}.`,
    suggestion: suggestionFor(snapshot),
  };
}
