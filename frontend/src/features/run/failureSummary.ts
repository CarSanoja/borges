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

function suggestionFor(snapshot: RunSnapshot): string {
  const error = snapshot.error ?? "";
  if (/smoke run|LogitResults|IndexError|AttributeError/.test(error)) {
    return "Try simplifying the question, or check that the outcome column holds the values you expect.";
  }
  return "Try again, simplify the question, or check the outcome column and the data you uploaded.";
}

export function failureSummary(snapshot: RunSnapshot): FailureSummary {
  const stage = currentStage(snapshot);
  const step = failedStep(snapshot);
  const where = stage ? `at the stage "${stageLabel(stage)}"` : "before the first stage";
  const at = step ? `, at the step "${step}"` : "";
  return {
    sentence: `The run stopped ${where}${at}.`,
    suggestion: suggestionFor(snapshot),
  };
}
