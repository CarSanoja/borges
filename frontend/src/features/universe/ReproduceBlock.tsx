import type { UniverseDetail } from "../../shared/types/contracts";
import { CopyButton } from "./CopyButton";
import { reproduceCommand } from "./reproduceCommand";

const HINT_CASE = "Run it from a fresh clone of the repository after uv sync: it re-executes this universe on the committed dataset and checks it against the recording.";
const HINT_SCRIPT = "Download the script, then run the command with a parquet copy of the data this run analysed.";

export function ReproduceBlock({ detail, hasRun }: { detail: UniverseDetail; hasRun: boolean }) {
  const command = detail.reproduce_command ? reproduceCommand(detail.reproduce_command) : "";
  const isCase = detail.reproduce_kind === "case";
  return (
    <section className="u-repro" aria-label="Reproduce">
      <p className="eyebrow">Reproduce</p>
      {command ? (
        <>
          <div className="u-repro-row">
            <code className="mono u-command">{command}</code>
            <CopyButton text={command} />
          </div>
          <p className="u-repro-hint">{isCase ? HINT_CASE : HINT_SCRIPT}</p>
        </>
      ) : (
        <p className="u-repro-hint">{hasRun ? "Preparing the reproduce command." : "Open a run on the server to get a runnable reproduce command."}</p>
      )}
      {detail.script_url && (
        <a className={isCase ? "link-btn u-download" : "btn btn-primary u-download"} href={detail.script_url} download={detail.script_filename ?? undefined}>
          Download script
        </a>
      )}
    </section>
  );
}
