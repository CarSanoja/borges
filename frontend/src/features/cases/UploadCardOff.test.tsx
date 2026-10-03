import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Health } from "../../shared/types/contracts";
import { UploadCard } from "./UploadCard";

const HEALTH = {
  status: "ok",
  llm: "scripted",
  llm_live_available: false,
  backend: "local",
  spend_usd: 0,
  spend_cap_usd: 5,
} as Health;

describe("UploadCard when uploads are off", () => {
  it("quotes the exact reason the server gives in /api/health", () => {
    const reason = "Uploads need live mode and this server has no NEBIUS_API_KEY.";
    render(<UploadCard health={{ ...HEALTH, uploads_available: false, uploads_unavailable_reason: reason }} onOpenRun={vi.fn()} />);
    expect(screen.getByRole("heading", { name: /off on this server/ })).toBeInTheDocument();
    expect(screen.getByTestId("upload-reason")).toHaveTextContent(reason);
    expect(screen.queryByLabelText(/Dataset/)).toBeNull();
    expect(screen.getByText("Your data")).toBeInTheDocument();
  });

  it("says the server is unreachable when there is no health at all", () => {
    render(<UploadCard health={null} onOpenRun={vi.fn()} />);
    expect(screen.getByTestId("upload-reason")).toHaveTextContent("The server is not reachable");
  });

  it("offers the form when uploads are available", () => {
    render(<UploadCard health={{ ...HEALTH, uploads_available: true }} onOpenRun={vi.fn()} />);
    expect(screen.getByLabelText(/Dataset/)).toBeInTheDocument();
    expect(screen.queryByTestId("upload-reason")).toBeNull();
  });
});
