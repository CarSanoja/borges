import { useState, type ChangeEvent, type FormEvent } from "react";
import { createRun, uploadDataset, type UploadResult } from "../../shared/api/client";
import type { Health } from "../../shared/types/contracts";
import { PiiSummary } from "./PiiSummary";
import { buildRequest, EMPTY_FORM, validateForm, type UploadForm } from "./uploadRequest";

const INSTEAD =
  "What the hosted demo can do instead: replay the recorded runs above, or run a curated case scripted on its own data.";
const OFFLINE_REASON = "The server is not reachable, so uploads are off.";

interface Props {
  health: Health | null;
  onOpenRun: (runId: string) => void;
}

export function UploadCard({ health, onOpenRun }: Props) {
  const available = health?.uploads_available === true;
  const reason = health ? (health.uploads_unavailable_reason ?? "Uploads are not enabled on this server.") : OFFLINE_REASON;
  const [form, setForm] = useState<UploadForm>(EMPTY_FORM);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<UploadResult | null>(null);

  const field = (key: keyof UploadForm) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const start = async (upload: UploadResult) => {
    const run = await createRun(buildRequest(upload.upload_id, form));
    onOpenRun(run.run_id);
  };

  const confirm = async () => {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      await start(pending);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start the run");
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const problem = validateForm(form, file);
    if (problem || !file) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      const upload = await uploadDataset(file);
      if (upload.pii && upload.pii.total_detections > 0) {
        setPending(upload);
        setBusy(false);
        return;
      }
      await start(upload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start the run");
      setBusy(false);
    }
  };

  return (
    <section className="upload-card" id="bring-your-own-data" aria-labelledby="upload-title">
      <p className="eyebrow">Your data</p>
      <h2 id="upload-title" className="case-title">
        Bring your own data{available ? "" : ": off on this server"}
      </h2>
      <p className="upload-lead">Upload a CSV or parquet file, say what you want to know and how you will decide. Borges runs the same live analysis on it.</p>
      {!available && (
        <div className="upload-unavailable" role="status">
          <p data-testid="upload-reason">
            <strong>Why it is off:</strong> {reason}
          </p>
          <p>{INSTEAD}</p>
        </div>
      )}
      {available && (
        <form onSubmit={submit} aria-label="Bring your own data">
          <fieldset disabled={busy} className="upload-fields">
            <label className="upload-field">
              <span>Dataset (CSV or parquet)</span>
              <input type="file" accept=".csv,.parquet,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
            <label className="upload-field">
              <span>Question</span>
              <textarea rows={2} value={form.question} onChange={field("question")} placeholder="Does the new onboarding raise activation?" />
            </label>
            <label className="upload-field">
              <span>Decision metric</span>
              <input value={form.metric} onChange={field("metric")} placeholder="activation lift, treatment minus control" />
            </label>
            <div className="upload-row">
              <label className="upload-field">
                <span>Positive when the estimate is</span>
                <select value={form.comparator} onChange={field("comparator")}>
                  <option value="gt">above the threshold</option>
                  <option value="lt">below the threshold</option>
                </select>
              </label>
              <label className="upload-field">
                <span>Threshold</span>
                <input inputMode="decimal" value={form.threshold} onChange={field("threshold")} />
              </label>
              <label className="upload-field">
                <span>Alpha</span>
                <input inputMode="decimal" value={form.alpha} onChange={field("alpha")} />
              </label>
            </div>
            <div className="upload-row">
              <label className="upload-field">
                <span>Positive verdict</span>
                <input value={form.positiveLabel} onChange={field("positiveLabel")} />
              </label>
              <label className="upload-field">
                <span>Negative verdict</span>
                <input value={form.negativeLabel} onChange={field("negativeLabel")} />
              </label>
            </div>
            <button type="submit" className="btn btn-primary">
              Start the analysis
            </button>
          </fieldset>
        </form>
      )}
      {pending?.pii && (
        <>
          <PiiSummary pii={pending.pii} />
          <button type="button" className="btn btn-primary" disabled={busy} onClick={confirm}>
            Start the analysis with these values redacted
          </button>
        </>
      )}
      {error && (
        <p className="case-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
