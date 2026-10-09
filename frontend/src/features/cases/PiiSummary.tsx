import type { PiiSummary as PiiSummaryData } from "../../shared/types/contracts";

const KIND_LABELS: Record<string, string> = {
  email: "email addresses",
  phone: "phone numbers",
  card: "card numbers",
  iban: "IBANs",
  ssn: "US SSNs",
  dni_nie: "Spanish DNI or NIE",
  curp: "CURP",
  rfc: "RFC",
  ip_address: "IP addresses",
  date_of_birth: "dates of birth",
  medical_record: "medical record numbers",
  person_name: "person names",
};

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}

interface Props {
  pii: PiiSummaryData;
}

export function PiiSummary({ pii }: Props) {
  if (pii.total_detections === 0) return null;
  return (
    <section className="pii-summary" aria-label="Personal data found in the upload" role="status">
      <h3 className="pii-title">Personal data found in {pii.columns.length === 1 ? "1 column" : `${pii.columns.length} columns`}</h3>
      <ul className="pii-columns">
        {pii.columns.map((column) => (
          <li key={column.column}>
            <span className="mono pii-column">{column.column}</span>
            <span className="pii-kinds">
              {Object.entries(column.kinds)
                .map(([kind, count]) => `${count} ${kindLabel(kind)}`)
                .join(", ")}
            </span>
            <span className="pii-scanned mono">
              of {column.scanned} {column.scanned < column.total_rows ? "sampled " : ""}values
            </span>
          </li>
        ))}
      </ul>
      <p className="pii-note">{pii.note}</p>
    </section>
  );
}
