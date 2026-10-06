import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Health } from "../../shared/types/contracts";
import { UploadCard } from "./UploadCard";

const base = {
  status: "ok",
  llm: "nebius",
  llm_live_available: true,
  backend: "contree",
  spend_usd: 1.234,
  spend_cap_usd: 5,
  uploads_available: true,
} as Health;

describe("UploadCost", () => {
  it("says a live upload run is billable, its typical cost and the remaining demo spend", () => {
    render(<UploadCard health={base} onOpenRun={() => undefined} />);
    const note = screen.getByTestId("upload-cost");
    expect(note).toHaveTextContent("live and billable");
    expect(note).toHaveTextContent("$0.02-0.06");
    expect(note).toHaveTextContent("$1.23 of $5.00");
  });

  it("says an upload is billable when replays are scripted but live models are available", () => {
    render(<UploadCard health={{ ...base, llm: "scripted" }} onOpenRun={() => undefined} />);
    expect(screen.getByTestId("upload-cost")).toHaveTextContent("live and billable");
  });

  it("says it is not billed when the server has no live models", () => {
    render(
      <UploadCard health={{ ...base, llm: "scripted", llm_live_available: false }} onOpenRun={() => undefined} />,
    );
    expect(screen.getByTestId("upload-cost")).toHaveTextContent("not billed here");
  });
});
