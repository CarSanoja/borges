import type { Comparator, DecisionRule, RunRequest } from "../../shared/types/contracts";

export interface UploadForm {
  question: string;
  metric: string;
  comparator: Comparator;
  threshold: string;
  alpha: string;
  positiveLabel: string;
  negativeLabel: string;
}

export const EMPTY_FORM: UploadForm = {
  question: "",
  metric: "",
  comparator: "gt",
  threshold: "0",
  alpha: "0.05",
  positiveLabel: "ACT",
  negativeLabel: "DO NOT ACT",
};

export function validateForm(form: UploadForm, file: File | null): string | null {
  if (!file) return "Choose a CSV or parquet file first.";
  if (!form.question.trim()) return "Write the question you want answered.";
  if (!form.metric.trim()) return "Describe the metric the decision rule reads.";
  if (!Number.isFinite(Number(form.threshold)) || form.threshold.trim() === "") return "The threshold must be a number.";
  const alpha = Number(form.alpha);
  if (!(alpha > 0 && alpha < 1)) return "Alpha must be between 0 and 1.";
  if (!form.positiveLabel.trim() || !form.negativeLabel.trim()) return "Both verdict labels are required.";
  return null;
}

export function buildRequest(uploadId: string, form: UploadForm): RunRequest {
  const decision_rule: DecisionRule = {
    metric: form.metric.trim(),
    comparator: form.comparator,
    threshold: Number(form.threshold),
    alpha: Number(form.alpha),
    positive_label: form.positiveLabel.trim(),
    negative_label: form.negativeLabel.trim(),
  };
  return { upload_id: uploadId, question: form.question.trim(), decision_rule, llm: "nebius" };
}
