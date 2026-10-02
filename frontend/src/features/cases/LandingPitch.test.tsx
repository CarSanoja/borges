import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../../shared/api/client";
import type { Health } from "../../shared/types/contracts";
import { FALLBACK_CASES } from "./fallbackCases";
import { PITCH } from "./Hero";
import { Landing } from "./Landing";

vi.mock("../../shared/api/client");

function health(extra: Partial<Health> = {}): Health {
  return {
    status: "ok",
    llm: "scripted",
    llm_live_available: false,
    backend: "local",
    spend_usd: 0,
    spend_cap_usd: 5,
    uploads_available: false,
    uploads_unavailable_reason: "Uploaded datasets run live and this server has no NEBIUS_API_KEY.",
    ...extra,
  };
}

function renderLanding() {
  const handlers = { onOpenRun: vi.fn(), onOpenReplay: vi.fn(), onOpenMock: vi.fn() };
  render(<Landing {...handlers} />);
  return handlers;
}

describe("Landing pitch and demo call to action", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(client.getCases).mockResolvedValue(FALLBACK_CASES);
    vi.mocked(client.getHealth).mockResolvedValue(health());
  });

  it("states what Borges does and for whom, with the demo CTA before the cases", async () => {
    const handlers = renderLanding();
    const pitch = screen.getByText(PITCH);
    expect(pitch.textContent).toMatch(/analysts and data teams/);
    const cta = screen.getByRole("button", { name: "Watch the 30-second demo" });
    const firstCase = await screen.findByLabelText("Cases");
    expect(cta.compareDocumentPosition(firstCase) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(pitch.compareDocumentPosition(cta) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await userEvent.click(cta);
    expect(handlers.onOpenReplay).toHaveBeenCalledWith("checkout_ab");
  });
});

describe("Bring your own data card", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(client.getCases).mockResolvedValue(FALLBACK_CASES);
  });

  it("is replaced by the exact server reason and the hosted alternative", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health());
    renderLanding();
    expect(await screen.findByText("Uploaded datasets run live and this server has no NEBIUS_API_KEY.")).toBeInTheDocument();
    expect(screen.getByText(/What the hosted demo can do instead/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start the analysis" })).toBeNull();
    expect(screen.queryByLabelText("Question")).toBeNull();
  });

  it("is replaced by an offline reason when the server cannot be reached", async () => {
    vi.mocked(client.getHealth).mockRejectedValue(new Error("down"));
    renderLanding();
    expect(await screen.findByText("The server is not reachable, so uploads are off.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start the analysis" })).toBeNull();
  });

  it("uploads the file, then starts a run with the question and the decision rule", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health({ uploads_available: true, uploads_unavailable_reason: null }));
    vi.mocked(client.uploadDataset).mockResolvedValue({ upload_id: "up1", profile: { name: "d", n_rows: 60, columns: [] } });
    vi.mocked(client.createRun).mockResolvedValue({ run_id: "r42" });
    const handlers = renderLanding();
    const start = await screen.findByRole("button", { name: "Start the analysis" });
    await waitFor(() => expect(start).toBeEnabled());
    expect(screen.queryByText(/What the hosted demo can do instead/)).toBeNull();

    const file = new File(["a,b\n1,2\n"], "sessions.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/Dataset/), file);
    await userEvent.type(screen.getByLabelText("Question"), "Does it lift activation?");
    await userEvent.type(screen.getByLabelText("Decision metric"), "activation lift");
    await userEvent.click(start);

    expect(client.uploadDataset).toHaveBeenCalledWith(file);
    expect(client.createRun).toHaveBeenCalledWith({
      upload_id: "up1",
      question: "Does it lift activation?",
      decision_rule: {
        metric: "activation lift",
        comparator: "gt",
        threshold: 0,
        alpha: 0.05,
        positive_label: "ACT",
        negative_label: "DO NOT ACT",
      },
      llm: "nebius",
    });
    await waitFor(() => expect(handlers.onOpenRun).toHaveBeenCalledWith("r42"));
  });

  it("asks for a file before uploading anything", async () => {
    vi.mocked(client.getHealth).mockResolvedValue(health({ uploads_available: true, uploads_unavailable_reason: null }));
    renderLanding();
    const start = await screen.findByRole("button", { name: "Start the analysis" });
    await waitFor(() => expect(start).toBeEnabled());
    await userEvent.click(start);
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a CSV or parquet file first.");
    expect(client.uploadDataset).not.toHaveBeenCalled();
  });
});
