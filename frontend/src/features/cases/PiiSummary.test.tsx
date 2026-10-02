import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PiiSummary as PiiSummaryData } from "../../shared/types/contracts";
import { PiiSummary } from "./PiiSummary";

const PII: PiiSummaryData = {
  columns: [
    { column: "contact", kinds: { email: 60 }, scanned: 60, total_rows: 60 },
    { column: "note", kinds: { phone: 3, ip_address: 1 }, scanned: 2000, total_rows: 9000 },
  ],
  total_detections: 64,
  note: "Counts come from a sample of each column and never include values.",
};

describe("PiiSummary", () => {
  it("lists each column with the kinds and counts, never values", () => {
    render(<PiiSummary pii={PII} />);
    const region = screen.getByRole("status", { name: "Personal data found in the upload" });
    expect(region).toHaveTextContent("Personal data found in 2 columns");
    expect(region).toHaveTextContent("contact");
    expect(region).toHaveTextContent("60 email addresses");
    expect(region).toHaveTextContent("3 phone numbers, 1 IP addresses");
    expect(region).toHaveTextContent("of 2000 sampled values");
    expect(region).toHaveTextContent("never include values");
  });

  it("renders nothing when no personal data was found", () => {
    const { container } = render(<PiiSummary pii={{ ...PII, columns: [], total_detections: 0 }} />);
    expect(container).toBeEmptyDOMElement();
  });
});
